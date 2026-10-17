"""Tests for POST /intake/voice-note and GET /intake/episodes/{id}.

House style: monkeypatch the wrapper function (app.sarvam.stt / app.sarvam.chat),
not the SDK internals, so these tests never touch the network.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app import audit, store
from app.api import intake
from app.main import app
from app.sarvam import chat, stt

client = TestClient(app)

HOUSEHOLD_ID = "hh_warangal_01"
AMMA = "p_amma"  # affected, te-IN, consented
SON = "p_son"  # responsible, en-IN, consented
SISTER = "p_sister"  # family_group, hi-IN, consented


@pytest.fixture(autouse=True)
def _reset_state():
    store.reset()
    audit.clear()
    yield


def _safe_transcription(text: str = "amma teliyajesindi, kaali ga undi") -> stt.TranscriptionResult:
    return stt.TranscriptionResult(
        transcript=text,
        language_code="te-IN",
        language_probability=0.97,
        stt_job_id=None,
        route="rest",
        source="sarvam",
    )


def _safe_summary(text: str = "The family reported how the affected person is feeling today.") -> chat.SummaryResult:
    return chat.SummaryResult(text=text, source="sarvam")


def _post_voice_note(monkeypatch, *, person_id: str = AMMA, household_id: str = HOUSEHOLD_ID,
                      transcription=None, summary=None, filename: str = "note.wav"):
    monkeypatch.setattr(intake.stt, "transcribe_rest", lambda *a, **kw: transcription or _safe_transcription())
    monkeypatch.setattr(intake.chat, "summarize", lambda *a, **kw: summary or _safe_summary())
    files = {"file": (filename, io.BytesIO(b"\x00\x00" * 100), "audio/wav")}
    data = {"household_id": household_id, "person_id": person_id}
    return client.post("/intake/voice-note", files=files, data=data)


def test_verbatim_text_stored_unaltered_and_not_refusal_validated(monkeypatch):
    # This sentence would fail refusal.validate() (names "sugar", a household
    # condition label, and states a dose) — but it is the person's own speech,
    # not agent-authored, so it must survive untouched.
    verbatim = "naaku sugar ekkuva, 500mg metformin రెండు సార్లు tinnanu"
    resp = _post_voice_note(monkeypatch, transcription=_safe_transcription(verbatim))
    assert resp.status_code == 200
    body = resp.json()
    assert body["verbatim_text"] == verbatim
    # The request still succeeds with a stored summary, because only the
    # *summary* text is gated, not the verbatim transcript.
    assert body["escalated"] is False

    episode_id = body["episode_id"]
    stored = store.utterances(episode_id)
    assert len(stored) == 1
    assert stored[0].verbatim_text == verbatim
    assert stored[0].speaker_label == "Lakshmi"  # p_amma's name


def test_summary_with_dose_is_rejected_and_escalated(monkeypatch):
    bad_summary = chat.SummaryResult(
        text="Take metformin 500mg twice a day for the sugar.", source="sarvam"
    )
    resp = _post_voice_note(monkeypatch, summary=bad_summary)
    assert resp.status_code == 200
    body = resp.json()

    assert body["escalated"] is True
    assert "escalation_reason" in body and body["escalation_reason"]
    assert "summary" not in body

    episode_id = body["episode_id"]
    # Verbatim utterance is kept regardless of the escalation.
    assert len(store.utterances(episode_id)) == 1
    # The rejected summary is never stored.
    assert store.summaries(episode_id) == []

    events = audit.events()
    assert any(e["action"] == "summary_refused" for e in events)
    assert not any(e["action"] == "summarize_voice_note" for e in events)


def test_summary_with_condition_is_rejected_and_escalated(monkeypatch):
    bad_summary = chat.SummaryResult(
        text="The family reports the patient's high blood pressure is worse.",
        source="sarvam",
    )
    resp = _post_voice_note(monkeypatch, summary=bad_summary)
    body = resp.json()

    assert body["escalated"] is True
    assert "high blood pressure" in body["escalation_reason"].lower() or "condition" in body["escalation_reason"].lower()
    episode_id = body["episode_id"]
    assert store.summaries(episode_id) == []


def test_keyterms_are_capped_at_fifty():
    many_names = [f"Medicine{i}" for i in range(60)]
    capped = stt.cap_keyterms(many_names)
    assert len(capped) == 50
    assert capped == many_names[:50]


def test_keyterms_under_fifty_are_not_padded():
    names = ["Telmisartan", "Metformin", "Atorvastatin"]
    assert stt.cap_keyterms(names) == names


def test_unconsented_person_is_refused(monkeypatch):
    hh = store.household(HOUSEHOLD_ID)
    hh.person(SISTER).consent_given_at = None

    monkeypatch.setattr(intake.stt, "transcribe_rest", lambda *a, **kw: _safe_transcription())
    monkeypatch.setattr(intake.chat, "summarize", lambda *a, **kw: _safe_summary())
    files = {"file": ("note.wav", io.BytesIO(b"\x00\x00" * 100), "audio/wav")}
    data = {"household_id": HOUSEHOLD_ID, "person_id": SISTER}
    resp = client.post("/intake/voice-note", files=files, data=data)

    assert resp.status_code == 403
    assert store.utterances() == []  # nothing stored before consent is checked


def test_unknown_household_is_404(monkeypatch):
    monkeypatch.setattr(intake.stt, "transcribe_rest", lambda *a, **kw: _safe_transcription())
    monkeypatch.setattr(intake.chat, "summarize", lambda *a, **kw: _safe_summary())
    files = {"file": ("note.wav", io.BytesIO(b"\x00\x00" * 100), "audio/wav")}
    data = {"household_id": "hh_does_not_exist", "person_id": AMMA}
    resp = client.post("/intake/voice-note", files=files, data=data)
    assert resp.status_code == 404


def test_unknown_person_is_404(monkeypatch):
    monkeypatch.setattr(intake.stt, "transcribe_rest", lambda *a, **kw: _safe_transcription())
    monkeypatch.setattr(intake.chat, "summarize", lambda *a, **kw: _safe_summary())
    files = {"file": ("note.wav", io.BytesIO(b"\x00\x00" * 100), "audio/wav")}
    data = {"household_id": HOUSEHOLD_ID, "person_id": "p_does_not_exist"}
    resp = client.post("/intake/voice-note", files=files, data=data)
    assert resp.status_code == 404


def test_mock_mode_is_tagged_on_stt(monkeypatch):
    monkeypatch.setattr(stt, "live", lambda: False)
    result = stt.transcribe_rest(b"\x00\x00", "note.wav", ["Telmisartan"])
    assert result.source == "mock"
    assert result.transcript  # the recorded fixture transcript, not empty


def test_mock_mode_is_tagged_on_chat(monkeypatch):
    monkeypatch.setattr(chat, "live", lambda: False)
    result = chat.summarize("some verbatim text", prescribed_medicines=["Metformin"])
    assert result.source == "mock"


def test_mock_mode_end_to_end_tags_response_source(monkeypatch):
    # Exercise the real mock branch through the endpoint (not a monkeypatched
    # wrapper) so the HTTP response itself carries source="mock".
    monkeypatch.setattr(intake.stt, "live", lambda: False)
    monkeypatch.setattr(intake.chat, "live", lambda: False)
    files = {"file": ("note.wav", io.BytesIO(b"\x00\x00" * 100), "audio/wav")}
    data = {"household_id": HOUSEHOLD_ID, "person_id": AMMA}
    resp = client.post("/intake/voice-note", files=files, data=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "mock"
    if body["escalated"] is False:
        assert body["summary"]["source"] == "mock"


def test_low_confidence_flags_human_confirmation(monkeypatch):
    low_conf = stt.TranscriptionResult(
        transcript="something unclear",
        language_code="te-IN",
        language_probability=0.4,
        stt_job_id=None,
        route="rest",
        source="sarvam",
    )
    resp = _post_voice_note(monkeypatch, transcription=low_conf)
    body = resp.json()
    assert body["needs_human_confirmation"] is True


def test_batch_route_used_over_thirty_seconds(monkeypatch):
    monkeypatch.setattr(intake.stt, "transcribe_batch", lambda *a, **kw: stt.TranscriptionResult(
        transcript="a long note",
        language_code="te-IN",
        language_probability=0.9,
        stt_job_id="job-123",
        route="batch",
        source="sarvam",
    ))
    monkeypatch.setattr(intake.chat, "summarize", lambda *a, **kw: _safe_summary())
    # 40 seconds of silence at 16kHz/16-bit mono has no fallback needed since
    # it's a real WAV header, well over the 30s REST ceiling.
    import struct

    sample_rate = 16000
    n_samples = sample_rate * 40
    data_size = n_samples * 2
    header = (
        b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
        + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
        + b"data" + struct.pack("<I", data_size)
    )
    wav_bytes = header + b"\x00" * data_size

    files = {"file": ("long_note.wav", io.BytesIO(wav_bytes), "audio/wav")}
    data = {"household_id": HOUSEHOLD_ID, "person_id": AMMA}
    resp = client.post("/intake/voice-note", files=files, data=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["stt_route"] == "batch"


def test_episode_record_visible_to_responsible_person(monkeypatch):
    resp = _post_voice_note(monkeypatch)
    episode_id = resp.json()["episode_id"]

    ok = client.get(
        f"/intake/episodes/{episode_id}",
        params={"household_id": HOUSEHOLD_ID, "person_id": SON},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["utterances"][0]["verbatim_text"] == _safe_transcription().transcript
    assert body["summaries"][0]["text_en"] == _safe_summary().text


def test_episode_record_hidden_from_family_group(monkeypatch):
    resp = _post_voice_note(monkeypatch)
    episode_id = resp.json()["episode_id"]

    forbidden = client.get(
        f"/intake/episodes/{episode_id}",
        params={"household_id": HOUSEHOLD_ID, "person_id": SISTER},
    )
    assert forbidden.status_code == 403
