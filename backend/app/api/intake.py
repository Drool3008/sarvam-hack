"""Voice-note intake (README "Listening" and "Triggered" stages).

`POST /intake/voice-note` transcribes a family voice note verbatim and writes
a separate, agent-authored English summary. `GET /intake/episodes/{id}`
returns both for the responsible person, so the split between the person's
own words and the agent's summary stays visible.

Rule 2/5: the verbatim `Utterance` is the person's own speech, not
agent-authored — it is never run through `refusal.validate()` and never
returned in a notification. Only the summary is agent-authored, and it is
gated by `refusal.validate()` before it is stored or returned.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import audit, store
from ..assess import refusal
from ..config import settings
from ..domain import Summary, Utterance
from ..sarvam import chat, stt

router = APIRouter(prefix="/intake", tags=["intake"])

# DECISION: no drug-NER is available in this slice, so the substitution check
# (the third refusal) scans the summary for a small lexicon of common generic
# names that could plausibly be confused with this household's prescribed
# medicines, plus the prescribed names themselves. This is a heuristic, not an
# exhaustive check — the real safety nets are the system prompt in
# app/sarvam/chat.py and the OPEN model-based second layer noted in
# app/assess/refusal.py.
_KNOWN_MEDICINE_LEXICON = {
    "telmisartan", "metformin", "atorvastatin",
    "glimepiride", "insulin", "amlodipine", "losartan", "paracetamol",
    "aspirin", "ibuprofen", "glibenclamide", "simvastatin", "rosuvastatin",
}


def _candidate_medicines(text: str) -> list[str]:
    lower = text.lower()
    return [name for name in _KNOWN_MEDICINE_LEXICON if re.search(rf"\b{name}\b", lower)]


def _episode_id() -> str:
    return uuid.uuid4().hex[:12]


def _audit_ref(event) -> dict:
    return {"action": event.action, "data_source": event.data_source, "at": event.at.isoformat()}


@router.post("/voice-note")
async def submit_voice_note(
    file: UploadFile = File(...),
    household_id: str = Form(...),
    person_id: str = Form(...),
    episode_id: str | None = Form(None),
) -> dict:
    hh = store.household(household_id)
    if hh is None:
        raise HTTPException(status_code=404, detail="unknown household")

    person = hh.person(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="unknown person")

    if not person.consented:
        # Rule 5 / prompt.md section 5: no data about a person is stored
        # before consent, voice notes included.
        raise HTTPException(status_code=403, detail="person has not consented")

    episode_id = episode_id or _episode_id()
    audio = await file.read()
    keyterms = stt.cap_keyterms(hh.medicine_names())

    # Duration is computed here only to record it on the audit trail;
    # stt.transcribe() makes its own REST/batch routing decision internally.
    duration_seconds, duration_is_estimate = stt.estimate_duration_seconds(audio)
    result = stt.transcribe(audio, file.filename or "voice_note.wav", keyterms)
    route = result.route

    utterance = Utterance.new(
        episode_id=episode_id,
        verbatim_text=result.transcript,
        language=result.language_code or person.preferred_language,
        speaker_label=person.name,
        audio_ref=file.filename,
        stt_job_id=result.stt_job_id,
    )
    store.add_utterance(utterance)
    transcribe_event = audit.record(
        "transcribe_voice_note",
        actor="system",
        data_source=f"saaras:{route}",
        episode_id=episode_id,
        household_id=household_id,
        person_id=person_id,
        route=route,
        source=result.source,
        duration_seconds=round(duration_seconds, 2),
        duration_is_estimate=duration_is_estimate,
    )
    audit_refs = [_audit_ref(transcribe_event)]

    summary_candidate = chat.summarize(
        result.transcript, prescribed_medicines=hh.medicine_names()
    )
    verdict = refusal.validate(
        summary_candidate.text,
        condition_labels=hh.condition_labels,
        prescribed_medicines=hh.medicine_names(),
        candidate_medicines=_candidate_medicines(summary_candidate.text),
    )

    escalated = not verdict.ok
    summary_out: dict | None = None
    if escalated:
        # Rule 2: discard the summary, keep the verbatim Utterance, escalate.
        escalation_event = audit.record(
            "summary_refused",
            actor="agent:sarvam-105b",
            data_source="voice_note_summary",
            episode_id=episode_id,
            household_id=household_id,
            person_id=person_id,
            violations=list(verdict.violations),
        )
        audit_refs.append(_audit_ref(escalation_event))
    else:
        summary = Summary(
            episode_id=episode_id,
            text_en=summary_candidate.text,
            created_from="voice_note",
        )
        store.add_summary(summary)
        summary_event = audit.record(
            "summarize_voice_note",
            actor="agent:sarvam-105b",
            data_source="voice_note_summary",
            episode_id=episode_id,
            household_id=household_id,
            person_id=person_id,
            source=summary_candidate.source,
        )
        audit_refs.append(_audit_ref(summary_event))
        summary_out = {"text_en": summary.text_en, "source": summary_candidate.source}

    confidence = result.language_probability
    needs_human_confirmation = (
        confidence is not None and confidence < settings().CONFIDENCE_THRESHOLD
    )

    response = {
        "episode_id": episode_id,
        "verbatim_text": utterance.verbatim_text,
        "language": utterance.language,
        "language_probability": confidence,
        "needs_human_confirmation": needs_human_confirmation,
        "source": result.source,
        "stt_route": route,
        "escalated": escalated,
        "audit_refs": audit_refs,
    }
    if escalated:
        response["escalation_reason"] = "; ".join(verdict.violations)
    else:
        response["summary"] = summary_out
    return response


@router.get("/episodes/{episode_id}")
def get_episode(episode_id: str, household_id: str, person_id: str) -> dict:
    """Verbatim Utterance(s) and Summary(ies) for one episode.

    Only the responsible person may read this record — the brief's full-detail
    audience from README's role-based visibility rule.
    """
    hh = store.household(household_id)
    if hh is None:
        raise HTTPException(status_code=404, detail="unknown household")

    person = hh.person(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="unknown person")

    if "responsible" not in person.roles:
        raise HTTPException(
            status_code=403, detail="only the responsible person can view an episode record"
        )

    episode_utterances = store.utterances(episode_id)
    episode_summaries = store.summaries(episode_id)
    if not episode_utterances:
        raise HTTPException(status_code=404, detail="unknown episode")

    audit.record(
        "view_episode",
        actor=person_id,
        data_source="episode_record",
        episode_id=episode_id,
        household_id=household_id,
    )

    return {
        "episode_id": episode_id,
        "utterances": [
            {
                "verbatim_text": u.verbatim_text,
                "language": u.language,
                "speaker_label": u.speaker_label,
                "audio_ref": u.audio_ref,
                "stt_job_id": u.stt_job_id,
                "created_at": u.created_at.isoformat(),
            }
            for u in episode_utterances
        ],
        "summaries": [
            {
                "text_en": s.text_en,
                "created_from": s.created_from,
                "created_at": s.created_at.isoformat(),
            }
            for s in episode_summaries
        ],
    }
