"""The Clinic agent's HTTP surface (README "Acting" stage; prompt.md section
9 Clinic agent row).

`POST /clinic/call` runs one clinic-booking episode — see
`app.voice_agents.clinic_call.run_clinic_call()` for the dialogue, the
redial/fallback/dead-end rule, and the hand-off. `GET /clinic/bookings`
reads back what happened for an episode.

Rule 8: the Sarvam model-API key and the Indus workspace key are read only
through `app.config.settings()`, never logged or returned here.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import store
from ..config import settings
from ..voice_agents.clinic_call import (
    ClinicCallResult,
    booking_to_dict,
    call_to_dict,
    run_clinic_call,
)
from ..voice_agents.platform import IndusNotConfigured

router = APIRouter(prefix="/clinic", tags=["clinic"])


class ClinicCallRequest(BaseModel):
    household_id: str
    episode_id: str | None = None
    reason: str
    requested_window: str
    scenario: str = "offers_slot"
    transport: str = Field(default="local", pattern="^(local|telephony)$")


def _episode_id() -> str:
    return uuid.uuid4().hex[:12]


def _result_dict(result: ClinicCallResult) -> dict:
    return {
        "episode_id": result.episode_id,
        "household_id": result.household_id,
        "transport": result.transport,
        "source": result.source,
        "scenario": result.scenario,
        "transcript": result.transcript,
        "clinic_reached": result.clinic_reached,
        "fell_through": result.fell_through,
        "fallback_reason": result.fallback_reason,
        "booking": result.booking,
        "call_ids": result.call_ids,
        "escalated": result.escalated,
        "escalation_reason": result.escalation_reason,
        "attempt_id": result.attempt_id,
    }


@router.post("/call")
def place_clinic_call(body: ClinicCallRequest) -> dict:
    hh = store.household(body.household_id)
    if hh is None:
        raise HTTPException(status_code=404, detail="unknown household")

    episode_id = body.episode_id or _episode_id()

    # DECISION: check Indus readiness here too, not only inside
    # platform.place_call(), so a telephony request with no workspace
    # configured gets one clear 503 naming the missing vars rather than a
    # 500 from an exception raised deeper in the call stack.
    if body.transport == "telephony" and not settings().indus_ready:
        missing = ", ".join(settings().missing_indus_vars())
        raise HTTPException(
            status_code=503,
            detail=f"Indus Voice Agents is not configured: missing {missing}",
        )

    try:
        result = run_clinic_call(
            household_id=body.household_id,
            episode_id=episode_id,
            reason=body.reason,
            requested_window=body.requested_window,
            transport=body.transport,
            scenario=body.scenario,
        )
    except IndusNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _result_dict(result)


@router.get("/bookings")
def list_bookings(episode_id: str) -> dict:
    bookings = store.bookings(episode_id)
    calls = store.calls(episode_id)
    return {
        "episode_id": episode_id,
        "bookings": [booking_to_dict(b) for b in bookings],
        "calls": [call_to_dict(c) for c in calls],
    }
