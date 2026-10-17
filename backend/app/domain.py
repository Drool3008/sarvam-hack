"""The slice of the section-5 data model these two functionalities touch.

Kept as dataclasses over an in-memory store for this build. The field names match
section 5 of prompt.md so the SQLAlchemy models can replace these without the
API or the wrappers changing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Audience = Literal["family_group", "responsible_person", "doctor"]
Role = Literal["affected", "responsible", "family_group"]


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Person:
    id: str
    household_id: str
    name: str
    phone_e164: str
    preferred_language: str          # BCP-47, e.g. "te-IN"
    second_language: str | None
    reads_roman_script: bool
    roles: set[Role]
    consent_given_at: datetime | None

    @property
    def consented(self) -> bool:
        return self.consent_given_at is not None


@dataclass
class Medicine:
    id: str
    person_id: str
    name: str
    strength: str
    dose_per_day: float


@dataclass
class Household:
    id: str
    city_pair: tuple[str, str]
    people: list[Person] = field(default_factory=list)
    medicines: list[Medicine] = field(default_factory=list)
    providers: list["Provider"] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    condition_labels: list[str] = field(default_factory=list)
    tts_dict_id: str | None = None

    def person(self, person_id: str) -> Person | None:
        return next((p for p in self.people if p.id == person_id), None)

    def medicine_names(self) -> list[str]:
        """Keyterms for Saaras. Capped at 50 by the caller (v4 limit)."""
        return [m.name for m in self.medicines]

    def clinics(self) -> list["Provider"]:
        """Clinics in rank order. Rank 2 is the fallback when rank 1 dead-ends."""
        return sorted(
            (p for p in self.providers if p.type == "clinic"), key=lambda p: p.rank
        )

    def affected_person(self) -> "Person | None":
        return next((p for p in self.people if "affected" in p.roles), None)

    def responsible_person(self) -> "Person | None":
        return next((p for p in self.people if "responsible" in p.roles), None)


@dataclass
class Provider:
    """A clinic, chemist or lab. Two of each per household, ranked."""

    id: str
    household_id: str
    city: str
    type: Literal["clinic", "chemist", "lab"]
    name: str
    phone_e164: str
    hours: str
    booking_notes: str
    rank: int


@dataclass
class Call:
    id: str
    episode_id: str
    agent: Literal["intake", "check_in", "clinic", "chemist"]
    attempt_id: str | None
    interaction_id: str | None
    to_phone: str
    status: Literal["connected", "no_answer", "busy", "failed"]
    duration: float | None
    final_agent_variables: dict
    recording_ref: str | None
    created_at: datetime = field(default_factory=_now)

    @staticmethod
    def new(**kw) -> "Call":
        return Call(id=_id(), **kw)


@dataclass
class Booking:
    episode_id: str
    provider_id: str
    slot: str
    confirmed_by_name: str | None
    status: Literal["held", "confirmed", "declined", "dead_end"]
    note: str | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Utterance:
    """The person's exact words. Never sent in a notification (rule 5)."""

    id: str
    episode_id: str
    verbatim_text: str
    language: str
    speaker_label: str
    audio_ref: str | None
    stt_job_id: str | None
    created_at: datetime = field(default_factory=_now)

    @staticmethod
    def new(**kw) -> "Utterance":
        return Utterance(id=_id(), **kw)


@dataclass
class Summary:
    episode_id: str
    text_en: str
    created_from: Literal["voice_note", "call"]
    created_at: datetime = field(default_factory=_now)


@dataclass
class Notification:
    id: str
    audience: Audience
    person_id: str
    language: str
    text: str
    audio_ref: str | None
    episode_id: str | None
    created_at: datetime = field(default_factory=_now)

    @staticmethod
    def new(**kw) -> "Notification":
        return Notification(id=_id(), **kw)
