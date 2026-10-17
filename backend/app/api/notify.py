"""POST /notify/spoken-update — the README "Checking in" stage.

Tells each audience what happened, in their own language, and — for the
affected (elderly) person specifically — gives them a spoken version too.

The role filter (prompt.md rule 5) is enforced here: which template an
audience gets is decided by this module, not by the caller, via
`notify.roles.build_status_text`. The resulting agent-authored text is gated
by `assess.refusal.enforce()` before anyone sees it (rule 2), translated
per recipient (`sarvam/translate.py`), and — only for the affected person,
when `speak` is set — spoken (`sarvam/tts.py`).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import audit, store
from ..assess.refusal import RefusalViolation, enforce
from ..config import settings
from ..domain import Notification, Person
from ..notify.roles import Event, build_status_text
from ..sarvam import translate, tts
from ..sarvam.tts import SpeechTextTooLong
from ..sarvam.translate import TranslateTextTooLong

router = APIRouter(prefix="/notify", tags=["notify"])

Audience = Literal["family_group", "responsible_person", "doctor"]
_ROLE_FOR_AUDIENCE = {"family_group": "family_group", "responsible_person": "responsible"}


class EventIn(BaseModel):
    kind: Literal["medicine_received", "appointment_booked"]
    medicine_name: str | None = None
    days_of_cover: int | None = None
    actor_name: str | None = None
    affected_name: str | None = None
    clinic_name: str | None = None
    when: str | None = None
    amount_inr: float | None = None
    detail: str | None = None


class SpokenUpdateRequest(BaseModel):
    household_id: str
    audience: Audience
    event: EventIn
    episode_id: str | None = None
    speak: bool = False


class RecipientResult(BaseModel):
    person_id: str
    name: str
    audience: Audience
    language: str
    text: str
    source_text_en: str
    audio_ref: str | None = None
    spoken_language: str | None = None
    fallback_reason: str | None = None
    spoken: bool = False
    source: str


class SpokenUpdateResponse(BaseModel):
    escalated: bool = False
    reason: str | None = None
    notifications: list[RecipientResult] = []


def _default_mode() -> str:
    return "sarvam" if settings().live else "mock"


@router.post("/spoken-update", response_model=SpokenUpdateResponse)
def spoken_update(req: SpokenUpdateRequest) -> SpokenUpdateResponse:
    if req.audience == "doctor":
        # DECISION: 501, not a half-built record — doctor hand-off (README
        # "Handing over") is out of scope for this build.
        raise HTTPException(status_code=501, detail="doctor audience is out of scope for this build")

    household = store.household(req.household_id)
    if household is None:
        raise HTTPException(status_code=404, detail=f"unknown household {req.household_id!r}")

    event = Event(
        kind=req.event.kind,
        medicine_name=req.event.medicine_name,
        days_of_cover=req.event.days_of_cover,
        actor_name=req.event.actor_name,
        affected_name=req.event.affected_name,
        clinic_name=req.event.clinic_name,
        when=req.event.when,
        amount_inr=req.event.amount_inr,
        detail=req.event.detail,
    )

    role_key = _ROLE_FOR_AUDIENCE[req.audience]
    recipients: list[Person] = [p for p in household.people if role_key in p.roles and p.consented]

    affected = next((p for p in household.people if "affected" in p.roles and p.consented), None)
    # DECISION: the affected (elderly) person is always a recipient, even on
    # a responsible_person call, so she can be told what happened too — but
    # only ever with the status-only template. She never gets a rupee figure
    # or a text she has no role for, same guarantee family_group gets.
    if affected is not None and affected.id not in {p.id for p in recipients}:
        recipients.append(affected)

    if not recipients:
        return SpokenUpdateResponse(notifications=[])

    def audience_for(person: Person) -> Audience:
        return req.audience if role_key in person.roles else "family_group"

    candidate_medicines = [event.medicine_name] if event.medicine_name else []
    texts: dict[str, str] = {}
    try:
        for person in recipients:
            aud = audience_for(person)
            if aud in texts:
                continue
            built = build_status_text(event, aud)
            enforce(
                built,
                condition_labels=household.condition_labels,
                prescribed_medicines=household.medicine_names(),
                candidate_medicines=candidate_medicines,
            )
            texts[aud] = built
    except RefusalViolation as exc:
        reason = "; ".join(exc.verdict.violations)
        audit.record(
            "notify.escalated",
            actor="notify_agent",
            data_source="agent_authored",
            household_id=household.id,
            audience=req.audience,
            episode_id=req.episode_id,
            reason=reason,
        )
        # DECISION: 200 with escalated=true, not 422 — a violation caught by
        # the refusal validator is the system working as designed (rule 2),
        # not a malformed request. Nothing is sent, per the BRIEF.
        return SpokenUpdateResponse(escalated=True, reason=reason, notifications=[])

    results: list[RecipientResult] = []
    for person in recipients:
        aud = audience_for(person)
        text_en = texts[aud]

        if person.preferred_language == "en-IN":
            translated_text, lang_used, translate_source = text_en, "en-IN", None
        else:
            try:
                t = translate.translate_text(
                    text_en,
                    person.preferred_language,
                    output_script="roman" if person.reads_roman_script else None,
                )
            except TranslateTextTooLong as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            translated_text, lang_used, translate_source = t.text, person.preferred_language, t.source

        spoken = False
        audio_ref = None
        spoken_language = None
        fallback_reason = None
        speech_source = None
        # DECISION: speak is for "the affected person" (BRIEF point 4) — an
        # elderly listener — not for family_group or responsible_person
        # recipients, who are assumed to read text.
        if req.speak and affected is not None and person.id == affected.id:
            try:
                speech = tts.speak(
                    text_en,
                    person.preferred_language,
                    second_language=person.second_language,
                    dict_id=household.tts_dict_id,
                )
            except SpeechTextTooLong as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            spoken = speech.spoken
            audio_ref = speech.audio_ref
            spoken_language = speech.spoken_language
            fallback_reason = speech.fallback_reason
            speech_source = speech.source

        sub_sources = [s for s in (translate_source, speech_source) if s is not None]
        entry_source = "mock" if "mock" in sub_sources else ("sarvam" if sub_sources else _default_mode())

        notification = Notification.new(
            audience=aud,
            person_id=person.id,
            language=lang_used,
            text=translated_text,
            audio_ref=audio_ref,
            episode_id=req.episode_id,
        )
        store.add_notification(notification)
        audit.record(
            "notify.sent",
            actor="notify_agent",
            data_source="agent_authored",
            household_id=household.id,
            person_id=person.id,
            audience=aud,
            language=lang_used,
            spoken=spoken,
            source=entry_source,
            episode_id=req.episode_id,
        )

        results.append(
            RecipientResult(
                person_id=person.id,
                name=person.name,
                audience=aud,
                language=lang_used,
                text=translated_text,
                source_text_en=text_en,
                audio_ref=audio_ref,
                spoken_language=spoken_language,
                fallback_reason=fallback_reason,
                spoken=spoken,
                source=entry_source,
            )
        )

    return SpokenUpdateResponse(notifications=results)


@router.get("/sent")
def sent(episode_id: str | None = None) -> dict:
    """What went to whom, so the role split is inspectable."""
    return {
        "notifications": [
            {
                "id": n.id,
                "audience": n.audience,
                "person_id": n.person_id,
                "language": n.language,
                "text": n.text,
                "audio_ref": n.audio_ref,
                "episode_id": n.episode_id,
                "created_at": n.created_at.isoformat(),
            }
            for n in store.notifications(episode_id)
        ]
    }
