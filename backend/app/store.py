"""In-memory household store seeded from fixtures/.

DECISION: this build runs on an in-memory store rather than PostgreSQL. The two
functionalities are read-mostly against the household and append-only against
Utterance / Summary / Notification, so Alembic and SQLAlchemy can land in
Milestone 0 without the API or the wrappers changing shape.

Rule 9: the seed file lives in fixtures/ and is loaded explicitly, never silently
substituted for a real household.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .domain import (
    Booking,
    Call,
    Household,
    Medicine,
    Notification,
    Person,
    Provider,
    Summary,
    Utterance,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

_households: dict[str, Household] = {}
_utterances: list[Utterance] = []
_summaries: list[Summary] = []
_notifications: list[Notification] = []
_calls: list[Call] = []
_bookings: list[Booking] = []


def _load(path: Path) -> Household:
    raw = json.loads(path.read_text())
    hh = Household(
        id=raw["id"],
        city_pair=tuple(raw["city_pair"]),
        red_flags=raw.get("red_flags", []),
        condition_labels=raw.get("condition_labels", []),
        tts_dict_id=raw.get("tts_dict_id"),
    )
    hh.people = [
        Person(
            id=p["id"],
            household_id=hh.id,
            name=p["name"],
            phone_e164=p["phone_e164"],
            preferred_language=p["preferred_language"],
            second_language=p.get("second_language"),
            reads_roman_script=p.get("reads_roman_script", False),
            roles=set(p.get("roles", [])),
            consent_given_at=(
                datetime.fromisoformat(p["consent_given_at"])
                if p.get("consent_given_at")
                else None
            ),
        )
        for p in raw.get("people", [])
    ]
    hh.medicines = [
        Medicine(
            id=m["id"],
            person_id=m["person_id"],
            name=m["name"],
            strength=m["strength"],
            dose_per_day=float(m["dose_per_day"]),
        )
        for m in raw.get("medicines", [])
    ]
    hh.providers = [
        Provider(
            id=pr["id"],
            household_id=hh.id,
            city=pr["city"],
            type=pr["type"],
            name=pr["name"],
            phone_e164=pr["phone_e164"],
            hours=pr.get("hours", ""),
            booking_notes=pr.get("booking_notes", ""),
            rank=int(pr.get("rank", 1)),
        )
        for pr in raw.get("providers", [])
    ]
    return hh


def reset(fixture: str = "household.json") -> None:
    _households.clear()
    _utterances.clear()
    _summaries.clear()
    _notifications.clear()
    _calls.clear()
    _bookings.clear()
    hh = _load(FIXTURES / fixture)
    _households[hh.id] = hh


def household(household_id: str) -> Household | None:
    if not _households:
        reset()
    return _households.get(household_id)


def households() -> list[Household]:
    if not _households:
        reset()
    return list(_households.values())


def add_utterance(u: Utterance) -> Utterance:
    _utterances.append(u)
    return u


def add_summary(s: Summary) -> Summary:
    _summaries.append(s)
    return s


def add_notification(n: Notification) -> Notification:
    _notifications.append(n)
    return n


def utterances(episode_id: str | None = None) -> list[Utterance]:
    return [u for u in _utterances if episode_id is None or u.episode_id == episode_id]


def summaries(episode_id: str | None = None) -> list[Summary]:
    return [s for s in _summaries if episode_id is None or s.episode_id == episode_id]


def notifications(episode_id: str | None = None) -> list[Notification]:
    return [n for n in _notifications if episode_id is None or n.episode_id == episode_id]


def add_call(c: Call) -> Call:
    _calls.append(c)
    return c


def add_booking(b: Booking) -> Booking:
    _bookings.append(b)
    return b


def calls(episode_id: str | None = None) -> list[Call]:
    return [c for c in _calls if episode_id is None or c.episode_id == episode_id]


def bookings(episode_id: str | None = None) -> list[Booking]:
    return [b for b in _bookings if episode_id is None or b.episode_id == episode_id]
