"""Role-based status templates (prompt.md section 10, README "Checking in").

`build_status_text` is pure: given the event and the audience, it returns
English text with no I/O and no Sarvam calls, so it is unit-testable on its
own. `family_group` is built from fixed templates with named slots — a field
the template has no slot for (`amount_inr`, `detail`, `days_of_cover`) simply
never reaches the text, by construction, not by filtering it out afterwards.
`responsible_person` gets every field, including every rupee.

The agent-authored text this module returns still has to pass
`app.assess.refusal.enforce()` before anyone sees it (rule 2) — that gate lives
in `app/api/notify.py`, not here, because this module has no business knowing
about escalation or audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EventKind = Literal["medicine_received", "appointment_booked"]
Audience = Literal["family_group", "responsible_person", "doctor"]


@dataclass(frozen=True)
class Event:
    """What happened. Only two kinds are modelled, matching the two status
    templates prompt.md section 10 gives verbatim — this build does not invent
    a free-text template."""

    kind: EventKind
    medicine_name: str | None = None
    days_of_cover: int | None = None
    actor_name: str | None = None  # who did it, e.g. "Ravi"
    affected_name: str | None = None  # who it concerns, e.g. "Lakshmi"
    clinic_name: str | None = None
    when: str | None = None
    amount_inr: float | None = None
    detail: str | None = None  # responsible_person only — never read by the family_group template


class DoctorAudienceNotSupported(Exception):
    """`doctor` is out of scope for this build (README "Handing over" stage)."""


def format_inr(amount: float) -> str:
    """₹ with Indian digit grouping: 1234567 -> '₹12,34,567', not '₹1,234,567'."""
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole = int(amount)
    paise = round((amount - whole) * 100)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        grouped = ",".join(groups) + "," + tail
    else:
        grouped = s
    if paise:
        grouped += f".{paise:02d}"
    return f"{sign}₹{grouped}"


def _family_group_text(event: Event) -> str:
    if event.kind == "medicine_received":
        medicine = event.medicine_name or "A medicine"
        who = event.actor_name or "a family member"
        return f"{medicine} was ordered and received by {who}."
    if event.kind == "appointment_booked":
        who = event.affected_name or "A family member"
        clinic = event.clinic_name or "the clinic"
        when = event.when or "the scheduled time"
        return f"{who} has an appointment at {clinic} on {when}."
    raise ValueError(f"no family_group template for event kind {event.kind!r}")  # pragma: no cover


def _responsible_person_text(event: Event) -> str:
    sentences = [_family_group_text(event)]
    if event.days_of_cover is not None:
        who = event.affected_name or "the patient"
        sentences.append(f"This gives {who} {event.days_of_cover} days of cover.")
    if event.amount_inr is not None:
        sentences.append(f"Amount spent: {format_inr(event.amount_inr)}.")
    if event.detail:
        sentences.append(event.detail)
    return " ".join(sentences)


def build_status_text(event: Event, audience: Audience) -> str:
    """The role filter (prompt.md rule 5: enforced here, not by the caller)."""
    if audience == "family_group":
        return _family_group_text(event)
    if audience == "responsible_person":
        return _responsible_person_text(event)
    if audience == "doctor":
        raise DoctorAudienceNotSupported("doctor audience is out of scope for this build")
    raise ValueError(f"unknown audience: {audience!r}")  # pragma: no cover
