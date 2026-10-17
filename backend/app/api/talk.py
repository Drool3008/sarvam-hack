"""Functionality 1: the person talks to the agent, and the agent talks back.

One turn of a conversation, end to end:

    voice in  -> Saaras v4 verbatim  -> Utterance (their exact words, kept)
              -> sarvam-105b strict assessment -> tier ratchet
              -> sarvam-105b reply  -> refusal validator
              -> Mayura + Bulbul v4 Flash -> voice out in their language

The verbatim transcript is the person's own speech and is deliberately NOT run
through the refusal validator: the parent is allowed to say "my sugar is high".
Everything the agent itself authors — the assessment's reason and summary, and
the spoken reply — is validated before anyone hears it.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import audit, store
from ..agent_prompts import LIVE_AGENT_BASE, REPLY_GOAL
from ..assess import refusal
from ..assess.assessment import AssessmentFailed, assess
from ..config import settings
from ..domain import Household, Person, Summary, Utterance
from ..sarvam import chat, stt, tts
from ..sarvam.client import SarvamUnavailable

log = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["talk"])

# DECISION: the episode's running tier lives in memory beside the store, which
# is itself in memory in this build. It exists so the ratchet has a previous
# tier to hold against across turns; it moves to the Episode row with the
# database.
_episode_tier: dict[str, str] = {}


def _resolve(household_id: str, person_id: str) -> tuple[Household, Person]:
    hh = store.household(household_id)
    if hh is None:
        raise HTTPException(404, f"unknown household {household_id!r}")
    person = hh.person(person_id)
    if person is None:
        raise HTTPException(404, f"unknown person {person_id!r} in {household_id!r}")
    if not person.consented:
        # Section 5: consent per adult, before anything about them is stored.
        raise HTTPException(403, f"{person.name} has not given consent; nothing was stored")
    return hh, person


def _prescribed(hh: Household, affected: Person | None) -> list[str]:
    return [m.name for m in hh.medicines if affected is None or m.person_id == affected.id]


def _handoff_text(hh: Household) -> str:
    """The one thing the agent may say when its own reply is refused.

    Built from a template rather than generated, so it cannot itself break a
    refusal. DECISION: the person on the other end must hear something, and
    silence would be worse than a hand-off sentence.
    """
    responsible = hh.responsible_person()
    who = responsible.name if responsible else "someone in the family"
    return (
        f"Thank you for telling me. I am not the right one to answer that, so I have "
        f"passed it to {who} to look at, and they will get back to you."
    )


def _reply(
    hh: Household, speaker: Person, verbatim: str, tier: str, escalated: bool
) -> tuple[str, str, bool]:
    """Generate the agent's reply and gate it. Returns (text, source, refused)."""
    affected = hh.affected_person()
    context = "\n".join(
        [
            f"You are speaking with {speaker.name} (roles {sorted(speaker.roles)}).",
            f"The person this concerns is {affected.name if affected else 'unknown'}.",
            f"Medicines already prescribed for them, which you may name: {_prescribed(hh, affected)}.",
            f"The assessed tier is {tier}." + (" A person has been asked about it." if escalated else ""),
            "",
            f"What they just said, word for word:\n{verbatim}",
        ]
    )
    result = chat.complete(
        [
            {"role": "system", "content": f"{LIVE_AGENT_BASE}\n\n{REPLY_GOAL}"},
            {"role": "user", "content": context},
        ],
        max_tokens=4096,
        mock_text=(
            "Thank you for telling me. I have made a note of it and I am passing it "
            "to the family now."
        ),
    )

    verdict = refusal.validate(
        result.text,
        condition_labels=hh.condition_labels,
        prescribed_medicines=_prescribed(hh, affected),
    )
    if not verdict:
        audit.record(
            "agent_reply_refused",
            actor="refusal_validator",
            data_source="sarvam-105b",
            violations=list(verdict.violations),
            household_id=hh.id,
        )
        log.warning("agent reply discarded: %s", verdict.violations)
        return _handoff_text(hh), result.source, True

    return result.text, result.source, False


@router.post("/talk")
async def talk(
    household_id: str = Form(...),
    person_id: str = Form(...),
    episode_id: str | None = Form(None),
    text: str | None = Form(None),
    speak: bool = Form(True),
    file: UploadFile | None = File(None),
) -> dict:
    """One conversation turn. Send `file` (audio) or `text`."""
    hh, person = _resolve(household_id, person_id)
    episode_id = episode_id or f"ep_{uuid.uuid4().hex[:10]}"
    affected = hh.affected_person()

    # --- what they said ---------------------------------------------------
    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(400, "the uploaded audio was empty")
        try:
            heard = stt.transcribe(
                data, file.filename or "note.wav", stt.cap_keyterms(hh.medicine_names())
            )
        except SarvamUnavailable as exc:
            raise HTTPException(502, f"speech to text failed: {exc}") from exc
        verbatim = heard.transcript
        language = heard.language_code or person.preferred_language
        confidence = heard.language_probability
        route = heard.route
        stt_source = heard.source
        stt_job_id = heard.stt_job_id
        audio_in = file.filename
    elif text and text.strip():
        verbatim = text.strip()
        language = person.preferred_language
        confidence = None
        route = "text"
        stt_source = "none"
        stt_job_id = None
        audio_in = None
    else:
        raise HTTPException(400, "send either `file` (audio) or `text`")

    utterance = store.add_utterance(
        Utterance.new(
            episode_id=episode_id,
            verbatim_text=verbatim,  # their words, stored unaltered and unvalidated
            language=language,
            speaker_label=person.id,
            audio_ref=audio_in,
            stt_job_id=stt_job_id,
        )
    )
    audit.record(
        "voice_note_transcribed" if audio_in else "message_received",
        actor=person.id,
        data_source=f"saaras:v4/{route}" if audio_in else "typed",
        episode_id=episode_id,
        utterance_id=utterance.id,
        source=stt_source,
    )

    # --- what it means ----------------------------------------------------
    trigger_kind = "affected_person" if affected and person.id == affected.id else "family_member"
    try:
        assessment = assess(
            household=hh,
            speaker=person,
            verbatim_text=verbatim,
            verbatim_ref=utterance.id,
            trigger_kind=trigger_kind,
            previous_tier=_episode_tier.get(episode_id),
        )
    except (AssessmentFailed, SarvamUnavailable) as exc:
        # Cannot tell is not a reason to go quiet: it is a reason to escalate.
        audit.record(
            "assessment_failed",
            actor="sarvam-105b",
            data_source="chat.completions",
            episode_id=episode_id,
            error=str(exc),
        )
        raise HTTPException(
            502,
            {
                "error": f"assessment failed: {exc}",
                "episode_id": episode_id,
                "verbatim_kept": True,
                "escalated": True,
            },
        ) from exc

    # The assessment's own prose is agent-authored, so it is gated too.
    prescribed = _prescribed(hh, affected)
    summary_verdict = refusal.validate(
        f"{assessment.reason}\n{assessment.summary}",
        condition_labels=hh.condition_labels,
        prescribed_medicines=prescribed,
    )
    summary_text: str | None = assessment.summary
    summary_refused = not summary_verdict.ok
    if summary_refused:
        summary_text = None
        audit.record(
            "assessment_text_refused",
            actor="refusal_validator",
            data_source="sarvam-105b",
            episode_id=episode_id,
            violations=list(summary_verdict.violations),
        )
    else:
        store.add_summary(
            Summary(episode_id=episode_id, text_en=assessment.summary, created_from="voice_note")
        )

    _episode_tier[episode_id] = assessment.tier
    audit.record(
        "assessed",
        actor="sarvam-105b",
        data_source="chat.completions/json_schema",
        episode_id=episode_id,
        tier=assessment.tier,
        factors_used=assessment.factors_used,
        escalated=assessment.escalated,
        ratchet=assessment.decision.reason,
    )

    # --- what it says back ------------------------------------------------
    reply_en, reply_source, reply_refused = _reply(
        hh, person, verbatim, assessment.tier, assessment.escalated
    )

    spoken: dict = {"spoken": False}
    if speak:
        try:
            said = tts.speak(
                reply_en,
                person.preferred_language,
                second_language=person.second_language,
                pace=0.8,  # slower, the listener may be elderly
                dict_id=hh.tts_dict_id,
            )
            spoken = {
                "spoken": said.spoken,
                "audio_ref": said.audio_ref,
                "spoken_language": said.spoken_language,
                "text_in_their_language": said.text,
                "fallback_reason": said.fallback_reason,
                "tts_source": said.source,
            }
            store.add_utterance(
                Utterance.new(
                    episode_id=episode_id,
                    verbatim_text=said.text or reply_en,
                    language=said.spoken_language or "en-IN",
                    speaker_label="agent",
                    audio_ref=said.audio_ref,
                    stt_job_id=None,
                )
            )
        except SarvamUnavailable as exc:
            # The reply still stands as text; only the voice failed.
            spoken = {"spoken": False, "error": f"speech failed: {exc}"}
            log.warning("tts failed for episode %s: %s", episode_id, exc)

    audit.record(
        "agent_replied",
        actor="family_health_agent",
        data_source="sarvam-105b + bulbul:v4-flash",
        episode_id=episode_id,
        refused=reply_refused,
        spoken=spoken.get("spoken", False),
    )

    escalations = []
    if assessment.escalated:
        escalations.append(f"tier {assessment.tier}: {assessment.decision.reason}")
    if reply_refused:
        escalations.append("the agent's own reply broke a refusal and was discarded")
    if summary_refused:
        escalations.append("the assessment's summary broke a refusal and was discarded")

    return {
        "episode_id": episode_id,
        "heard": {
            "verbatim": verbatim,  # exactly what they said
            "language": language,
            "language_confidence": confidence,
            "needs_human_confirmation": bool(
                confidence is not None and confidence < settings().CONFIDENCE_THRESHOLD
            ),
            "route": route,
            "utterance_id": utterance.id,
            "source": stt_source,
        },
        "assessment": {
            "trigger_kind": assessment.trigger_kind,
            "account_type": assessment.account_type,
            "tier": assessment.tier,
            "factors_used": assessment.factors_used,
            "reason": assessment.reason if not summary_refused else None,
            "summary": summary_text,
            "escalated": assessment.escalated,
            "ratchet": assessment.decision.reason,
            "source": assessment.sarvam_source,
        },
        "reply": {
            "text_en": reply_en,
            "refused_and_replaced": reply_refused,
            "source": reply_source,
            **spoken,
        },
        "escalations": escalations,
    }


@router.get("/conversation/{episode_id}")
def conversation(episode_id: str) -> dict:
    """The turns of one episode, in order, with the verbatim record intact."""
    turns = [
        {
            "utterance_id": u.id,
            "speaker": u.speaker_label,
            "language": u.language,
            "verbatim": u.verbatim_text,
            "audio_ref": u.audio_ref,
            "at": u.created_at.isoformat(),
        }
        for u in store.utterances(episode_id)
    ]
    return {
        "episode_id": episode_id,
        "tier": _episode_tier.get(episode_id),
        "turns": turns,
        "summaries": [s.text_en for s in store.summaries(episode_id)],
    }
