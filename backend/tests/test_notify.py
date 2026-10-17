"""Tests for the role-filtered spoken status update (README "Checking in").

House style: mock at the wrapper boundary. `translate.translate_text` and
`tts.speak` are monkeypatched as module attributes (not SDK internals), since
`app/api/notify.py` calls them as `translate.translate_text(...)` /
`tts.speak(...)`, never via a name-level import.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import audit, store
from app.domain import Household, Medicine, Person
from app.main import app
from app.notify import roles
from app.sarvam import translate, tts

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state():
    store.reset()
    audit.clear()
    yield


# --- roles.build_status_text: the pure role filter -------------------------


def test_family_group_strips_money_and_medical_detail():
    event = roles.Event(
        kind="medicine_received",
        medicine_name="Metformin",
        actor_name="Ravi",
        amount_inr=4500.0,
        detail="she has high blood pressure, take 2 tablets twice a day",
    )
    text = roles.build_status_text(event, "family_group")

    assert text == "Metformin was ordered and received by Ravi."
    assert "₹" not in text
    assert "4500" not in text
    assert "blood pressure" not in text.lower()
    assert "tablet" not in text.lower()


def test_family_group_appointment_template():
    event = roles.Event(kind="appointment_booked", affected_name="Lakshmi", clinic_name="Sunrise Polyclinic", when="Friday 10am")
    text = roles.build_status_text(event, "family_group")
    assert text == "Lakshmi has an appointment at Sunrise Polyclinic on Friday 10am."


def test_responsible_person_includes_every_rupee():
    event = roles.Event(
        kind="medicine_received",
        medicine_name="Metformin",
        actor_name="Ravi",
        affected_name="Lakshmi",
        days_of_cover=10,
        amount_inr=1234.50,
    )
    text = roles.build_status_text(event, "responsible_person")

    assert "₹1,234.50" in text
    assert "10 days of cover" in text


def test_format_inr_indian_grouping():
    assert roles.format_inr(123456) == "₹1,23,456"
    assert roles.format_inr(1234.5) == "₹1,234.50"
    assert roles.format_inr(99) == "₹99"


def test_doctor_audience_raises_in_role_filter():
    event = roles.Event(kind="medicine_received", medicine_name="Metformin", actor_name="Ravi")
    with pytest.raises(roles.DoctorAudienceNotSupported):
        roles.build_status_text(event, "doctor")


# --- translate.py: chunking refuses rather than truncates -------------------


def test_translate_refuses_when_single_sentence_too_long():
    long_text = "x" * (translate.MAYURA_CHAR_LIMIT + 1)
    with pytest.raises(translate.TranslateTextTooLong):
        translate.translate_text(long_text, "hi-IN")


# --- /notify/spoken-update -------------------------------------------------


def test_doctor_audience_returns_501():
    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_warangal_01",
            "audience": "doctor",
            "event": {"kind": "medicine_received", "medicine_name": "Metformin", "actor_name": "Ravi"},
        },
    )
    assert resp.status_code == 501


def test_dose_in_payload_is_refused_and_escalated(monkeypatch):
    def _unexpected(*args, **kwargs):
        raise AssertionError("translate_text must not run after an escalation")

    monkeypatch.setattr(translate, "translate_text", _unexpected)

    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_warangal_01",
            "audience": "responsible_person",
            "event": {
                "kind": "medicine_received",
                "medicine_name": "Metformin",
                "actor_name": "Ravi",
                "detail": "take 2 tablets twice a day",
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] is True
    assert "dose" in body["reason"]
    assert body["notifications"] == []
    assert store.notifications() == []
    assert any(e["action"] == "notify.escalated" for e in audit.events())


def test_condition_name_in_family_group_template_field_is_refused():
    # "Metformin 500mg" flows into the family_group template via
    # medicine_name itself, so even the status-only template is protected.
    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_warangal_01",
            "audience": "family_group",
            "event": {"kind": "medicine_received", "medicine_name": "Metformin 500mg", "actor_name": "Ravi"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] is True


def test_skips_translation_call_for_english_recipient(monkeypatch):
    def guarded(text, target_language_code, *, source_language_code="en-IN", output_script=None):
        assert target_language_code != "en-IN", "must not translate when target is already en-IN"
        return translate.TranslateResult(
            text=f"[{target_language_code}] {text}",
            model="mayura:v1",
            source_language_code=source_language_code,
            output_script_applied=False,
            source="mock",
        )

    monkeypatch.setattr(translate, "translate_text", guarded)

    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_warangal_01",
            "audience": "responsible_person",
            "event": {
                "kind": "medicine_received",
                "medicine_name": "Metformin",
                "actor_name": "Ravi",
                "affected_name": "Lakshmi",
                "days_of_cover": 10,
                "amount_inr": 500.0,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    ravi = next(n for n in body["notifications"] if n["person_id"] == "p_son")
    assert ravi["language"] == "en-IN"
    assert "₹500" in ravi["text"]


def test_mock_source_is_tagged_in_response(monkeypatch):
    monkeypatch.setattr(
        translate,
        "translate_text",
        lambda *a, **kw: translate.TranslateResult(
            text="mock translated text",
            model="mayura:v1",
            source_language_code="en-IN",
            output_script_applied=False,
            source="mock",
        ),
    )

    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_warangal_01",
            "audience": "family_group",
            "event": {"kind": "medicine_received", "medicine_name": "Metformin", "actor_name": "Ravi"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    non_english = [n for n in body["notifications"] if n["language"] != "en-IN"]
    assert non_english
    assert all(n["source"] == "mock" for n in non_english)


def test_malayalam_second_language_fallback(monkeypatch):
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    affected = Person(
        id="p_test_ml",
        household_id="hh_test",
        name="Amma",
        phone_e164="+910000000000",
        preferred_language="ml-IN",
        second_language="hi-IN",
        reads_roman_script=False,
        roles={"affected"},
        consent_given_at=now,
    )
    custom_household = Household(
        id="hh_test",
        city_pair=("A", "B"),
        people=[affected],
        medicines=[Medicine(id="m1", person_id="p_test_ml", name="Metformin", strength="500mg", dose_per_day=2)],
        red_flags=[],
        condition_labels=[],
        tts_dict_id=None,
    )
    monkeypatch.setattr(store, "household", lambda hid: custom_household)
    monkeypatch.setattr(
        translate,
        "translate_text",
        lambda text, target_language_code, **kw: translate.TranslateResult(
            text=f"[{target_language_code}] {text}",
            model="mayura:v1",
            source_language_code="en-IN",
            output_script_applied=False,
            source="mock",
        ),
    )

    def fake_speak(text, language_code, *, source_language_code="en-IN", second_language=None, pace=0.8, dict_id=None):
        assert language_code == "ml-IN"
        assert second_language == "hi-IN"
        return tts.SpeechResult(
            audio_ref="out/fake.wav",
            spoken_language="hi-IN",
            fallback_reason=f"{language_code} is not covered by bulbul:v4-flash; speaking in second_language {second_language} instead",
            spoken=True,
            source="mock",
            text=f"[hi-IN] {text}",
        )

    monkeypatch.setattr(tts, "speak", fake_speak)

    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_test",
            "audience": "family_group",
            "event": {"kind": "medicine_received", "medicine_name": "Metformin", "actor_name": "Ravi"},
            "speak": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    entry = next(n for n in body["notifications"] if n["person_id"] == "p_test_ml")

    assert entry["language"] == "ml-IN"  # the written text stays in her preferred language
    assert entry["spoken"] is True
    assert entry["spoken_language"] == "hi-IN"  # but speech falls back to second_language
    assert entry["fallback_reason"] is not None
    assert "ml-IN" in entry["fallback_reason"]
    assert entry["audio_ref"] == "out/fake.wav"


def test_odia_with_no_coverable_second_language_is_not_spoken(monkeypatch):
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    affected = Person(
        id="p_test_od",
        household_id="hh_test2",
        name="Appa",
        phone_e164="+910000000001",
        preferred_language="od-IN",
        second_language="ml-IN",  # also uncovered by bulbul:v4-flash
        reads_roman_script=False,
        roles={"affected"},
        consent_given_at=now,
    )
    custom_household = Household(
        id="hh_test2",
        city_pair=("A", "B"),
        people=[affected],
        medicines=[Medicine(id="m1", person_id="p_test_od", name="Metformin", strength="500mg", dose_per_day=2)],
        red_flags=[],
        condition_labels=[],
        tts_dict_id=None,
    )
    monkeypatch.setattr(store, "household", lambda hid: custom_household)
    monkeypatch.setattr(
        translate,
        "translate_text",
        lambda text, target_language_code, **kw: translate.TranslateResult(
            text=f"[{target_language_code}] {text}",
            model="sarvam-translate:v1",
            source_language_code="en-IN",
            output_script_applied=False,
            source="mock",
        ),
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("tts.speak must not reach a real/mock synth call when neither language is covered")

    # speak() itself decides not to call anything further when neither
    # language is covered — it is not monkeypatched away here, so this test
    # exercises the real function body down to that early return.
    resp = client.post(
        "/notify/spoken-update",
        json={
            "household_id": "hh_test2",
            "audience": "family_group",
            "event": {"kind": "medicine_received", "medicine_name": "Metformin", "actor_name": "Ravi"},
            "speak": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    entry = next(n for n in body["notifications"] if n["person_id"] == "p_test_od")
    assert entry["spoken"] is False
    assert entry["audio_ref"] is None
    assert entry["fallback_reason"] is not None
    assert "od-IN" in entry["fallback_reason"]
    assert "ml-IN" in entry["fallback_reason"]
