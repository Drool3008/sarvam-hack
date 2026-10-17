"""Tests for POST /clinic/call and GET /clinic/bookings.

House style: monkeypatch the wrapper function (app.sarvam.conversations),
not the SDK internals, so these tests never touch the network. The API is
exercised through a standalone FastAPI app that only mounts clinic.router,
because app/main.py is owned by another agent and is not edited here.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import audit, store
from app.api import clinic as clinic_api
from app.sarvam import conversations
from app.voice_agents import clinic_call
from app.voice_agents.platform import IndusNotConfigured

app = FastAPI()
app.include_router(clinic_api.router)
client = TestClient(app)

HOUSEHOLD_ID = "hh_warangal_01"
AFFECTED_NAME = "Lakshmi"  # p_amma
CLINIC_RANK_1 = "cl_sunrise"
CLINIC_RANK_2 = "cl_kakatiya"


@pytest.fixture(autouse=True)
def _reset_state():
    store.reset()
    audit.clear()
    yield


def _patch_dialogue(monkeypatch, texts: list[str] | None = None):
    """Deterministic, refusal-safe agent turns, in call order."""
    texts = texts or []
    calls = {"n": 0}

    def fake(messages, max_tokens=1024):
        idx = calls["n"]
        calls["n"] += 1
        text = texts[idx] if idx < len(texts) else f"Agent turn {idx + 1}, calling about the appointment."
        return conversations.ConversationTurn(text=text, source="sarvam")

    monkeypatch.setattr(clinic_call.conversations, "next_turn", fake)


def _call_body(**overrides) -> dict:
    body = {
        "household_id": HOUSEHOLD_ID,
        "reason": "she has not been feeling well",
        "requested_window": "tomorrow morning",
        "scenario": "offers_slot",
        "transport": "local",
    }
    body.update(overrides)
    return body


# --------------------------------------------------------------------------- #
# Happy path: slot offered in the requested window, hand-off confirmed
# --------------------------------------------------------------------------- #


def test_offers_slot_confirms_booking_with_named_human(monkeypatch):
    _patch_dialogue(monkeypatch)
    resp = client.post("/clinic/call", json=_call_body())
    assert resp.status_code == 200
    body = resp.json()

    assert body["transport"] == "local"
    assert body["escalated"] is False
    assert body["fell_through"] is False
    assert body["clinic_reached"]["id"] == CLINIC_RANK_1

    booking = body["booking"]
    assert booking["status"] == "confirmed"
    assert booking["confirmed_by_name"] == AFFECTED_NAME
    assert booking["slot"] == "tomorrow 10:00 AM"

    speakers = [t["speaker"] for t in body["transcript"]]
    assert speakers[-1] == "affected_person"
    assert AFFECTED_NAME in body["transcript"][-1]["text"]

    # The hand-off confirmation is the parent's own words, not agent-authored
    # — it must never be run through the refusal validator's lexicon as if it
    # were agent text, and it must be stored as an Utterance.
    stored = store.utterances(body["episode_id"])
    hand_off = [u for u in stored if u.speaker_label == "affected_person"]
    assert len(hand_off) == 1
    assert hand_off[0].verbatim_text == body["transcript"][-1]["text"]


def test_booking_never_confirmed_without_confirmed_by_name(monkeypatch):
    # Escalate right on the hand-off turn (turn 3) so the booking is already
    # "held" when the call ends — it must not reach "confirmed" without the
    # named human hand-off turn actually happening.
    _patch_dialogue(monkeypatch, texts=["Good morning.", "That slot works well."])
    monkeypatch.setattr(
        clinic_call.conversations,
        "next_turn",
        lambda messages, max_tokens=1024: (
            conversations.ConversationTurn(text="Good morning.", source="sarvam")
            if sum(1 for m in messages if m["role"] == "assistant") == 0
            else conversations.ConversationTurn(text="That slot works well.", source="sarvam")
            if sum(1 for m in messages if m["role"] == "assistant") == 1
            else conversations.ConversationTurn(
                text="She has diabetes and takes 500mg metformin twice a day.",
                source="sarvam",
            )
        ),
    )
    resp = client.post("/clinic/call", json=_call_body())
    assert resp.status_code == 200
    body = resp.json()

    assert body["escalated"] is True
    booking = body["booking"]
    assert booking["status"] == "held"
    assert booking["confirmed_by_name"] is None

    # No episode anywhere in the store ever has a confirmed booking without
    # a named confirmer.
    for b in store.bookings(body["episode_id"]):
        if b.status == "confirmed":
            assert b.confirmed_by_name


# --------------------------------------------------------------------------- #
# No slot in the requested window: next option taken, with a reason
# --------------------------------------------------------------------------- #


def test_no_slot_in_window_records_which_option_and_why(monkeypatch):
    _patch_dialogue(monkeypatch)
    resp = client.post("/clinic/call", json=_call_body(scenario="no_slot_offers_later"))
    assert resp.status_code == 200
    body = resp.json()

    booking = body["booking"]
    assert booking["slot"] == "Thursday 18:00"
    assert booking["status"] == "confirmed"  # the hand-off still happens for the later slot
    assert booking["note"] is not None
    assert "Thursday 18:00" in booking["note"]
    assert "tomorrow morning" in booking["note"]  # the originally requested window, for "why"


# --------------------------------------------------------------------------- #
# Clinic will not answer: redial, then the second clinic, then dead end
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("scenario", ["no_answer", "busy"])
def test_unreachable_clinic_redials_then_falls_through_to_dead_end(monkeypatch, scenario):
    _patch_dialogue(monkeypatch)  # should never be called — nobody ever answers
    resp = client.post("/clinic/call", json=_call_body(scenario=scenario))
    assert resp.status_code == 200
    body = resp.json()

    assert body["escalated"] is False
    assert body["fell_through"] is True
    assert body["clinic_reached"] is None
    assert body["booking"]["status"] == "dead_end"
    # It never stops silently: the dead end is explicitly reported.
    assert body["booking"]["note"]

    calls = store.calls(body["episode_id"])
    assert len(calls) == 3  # rank-1 attempt, rank-1 redial, rank-2 attempt
    assert calls[0].to_phone == calls[1].to_phone  # same clinic redialed
    assert calls[2].to_phone != calls[0].to_phone  # then the second clinic
    assert all(c.status == scenario for c in calls)

    events = [e["action"] for e in audit.events()]
    assert events.count("clinic_call_attempt") == 3
    assert "clinic_dead_end" in events

    # No conversation turn was ever generated — nobody answered the phone.
    assert body["transcript"]
    assert all(t["speaker"] == "system" for t in body["transcript"])


# --------------------------------------------------------------------------- #
# The three refusals, on a live-call line
# --------------------------------------------------------------------------- #


def test_agent_line_naming_a_condition_is_blocked_and_escalated(monkeypatch):
    monkeypatch.setattr(
        clinic_call.conversations,
        "next_turn",
        lambda messages, max_tokens=1024: conversations.ConversationTurn(
            text="I'm calling because Lakshmi has high blood pressure.", source="sarvam"
        ),
    )
    resp = client.post("/clinic/call", json=_call_body())
    assert resp.status_code == 200
    body = resp.json()

    assert body["escalated"] is True
    assert body["escalation_reason"]
    assert "condition" in body["escalation_reason"].lower()
    assert body["booking"] is None
    # The violating line is never spoken: it is not in the transcript, and no
    # agent Utterance was stored for it.
    assert not any(t["speaker"] == "agent" for t in body["transcript"])
    assert not any(u.speaker_label == "agent" for u in store.utterances(body["episode_id"]))

    events = [e["action"] for e in audit.events()]
    assert "clinic_call_refusal_violation" in events


def test_agent_line_suggesting_a_dose_is_blocked_and_escalated(monkeypatch):
    monkeypatch.setattr(
        clinic_call.conversations,
        "next_turn",
        lambda messages, max_tokens=1024: conversations.ConversationTurn(
            text="Please tell the doctor she needs 500mg metformin twice a day.",
            source="sarvam",
        ),
    )
    resp = client.post("/clinic/call", json=_call_body())
    body = resp.json()

    assert body["escalated"] is True
    assert "dose" in body["escalation_reason"].lower()
    assert body["booking"] is None


# --------------------------------------------------------------------------- #
# Telephony transport without an Indus workspace
# --------------------------------------------------------------------------- #


def test_telephony_transport_raises_indus_not_configured_naming_missing_vars():
    with pytest.raises(IndusNotConfigured) as exc_info:
        clinic_call.run_clinic_call(
            household_id=HOUSEHOLD_ID,
            episode_id="ep_telephony_1",
            reason="she has not been feeling well",
            requested_window="tomorrow morning",
            transport="telephony",
        )
    message = str(exc_info.value)
    assert "SARVAM_VA_API_KEY" in message
    assert "SARVAM_ORG_ID" in message
    assert "SARVAM_WORKSPACE_ID" in message


def test_telephony_transport_via_api_returns_503_with_missing_vars():
    resp = client.post("/clinic/call", json=_call_body(transport="telephony"))
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert "SARVAM_VA_API_KEY" in detail
    assert "SARVAM_ORG_ID" in detail
    assert "SARVAM_WORKSPACE_ID" in detail


# --------------------------------------------------------------------------- #
# GET /clinic/bookings
# --------------------------------------------------------------------------- #


def test_get_bookings_returns_booking_and_call_rows(monkeypatch):
    _patch_dialogue(monkeypatch)
    posted = client.post("/clinic/call", json=_call_body()).json()
    episode_id = posted["episode_id"]

    resp = client.get("/clinic/bookings", params={"episode_id": episode_id})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["bookings"]) == 1
    assert body["bookings"][0]["status"] == "confirmed"
    assert len(body["calls"]) == 1
    assert body["calls"][0]["status"] == "connected"


def test_unknown_household_is_404():
    resp = client.post("/clinic/call", json=_call_body(household_id="hh_does_not_exist"))
    assert resp.status_code == 404


def test_unknown_scenario_is_400(monkeypatch):
    _patch_dialogue(monkeypatch)
    resp = client.post("/clinic/call", json=_call_body(scenario="not_a_real_scenario"))
    assert resp.status_code == 400
