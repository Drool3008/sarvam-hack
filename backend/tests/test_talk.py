"""Functionality 1: the person talks to the agent and the agent talks back.

Sarvam is mocked at the wrapper boundary — `stt.transcribe`, `chat.complete`
and `tts.speak` — so these tests make no network call.
"""

import pytest
from fastapi.testclient import TestClient

from app import audit, store
from app.assess.assessment import _MOCK_ASSESSMENT
from app.main import app
from app.sarvam import chat, stt, tts

HH = "hh_warangal_01"


@pytest.fixture(autouse=True)
def _clean():
    store.reset()
    audit.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _fake_heard(transcript: str, *, language="te-IN", probability=0.99, route="rest"):
    return stt.TranscriptionResult(
        transcript=transcript,
        language_code=language,
        language_probability=probability,
        stt_job_id=None,
        route=route,
        source="mock",
    )


def _fake_speech(text: str, *, language="te-IN", spoken=True, fallback=None):
    return tts.SpeechResult(
        audio_ref="out/test.wav" if spoken else None,
        spoken_language=language if spoken else None,
        fallback_reason=fallback,
        spoken=spoken,
        source="mock",
        text=text,
    )


def _stub_chat(monkeypatch, *, reply: str):
    """`complete` serves the assessment when given a schema, else the reply."""

    def fake(messages, *, max_tokens=4096, model="sarvam-105b", response_format=None,
             reasoning_effort=None, mock_text=None):
        if response_format is not None:
            return chat.ChatResult(text=_MOCK_ASSESSMENT, source="mock")
        return chat.ChatResult(text=reply, source="mock")

    monkeypatch.setattr(chat, "complete", fake)
    # assessment.py imported `chat` as a module, so patching the attribute is enough
    return fake


# --- the happy turn ------------------------------------------------------

def test_a_voice_note_is_heard_assessed_and_answered(client, monkeypatch):
    said = "అమ్మ అంటోంది కాళ్ళు వాచాయి మూడు రోజుల నుంచి"
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard(said))
    _stub_chat(monkeypatch, reply="Thank you for telling me. I am passing this to Ravi now.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech("తెలుగు సమాధానం"))

    r = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma", "speak": "true"},
        files={"file": ("note.wav", b"RIFFfake", "audio/wav")},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["heard"]["verbatim"] == said          # their exact words, unaltered
    assert body["heard"]["language"] == "te-IN"
    assert body["assessment"]["tier"] in ("elevated", "urgent", "critical")
    assert body["reply"]["refused_and_replaced"] is False
    assert body["reply"]["spoken"] is True
    assert body["reply"]["spoken_language"] == "te-IN"


def test_the_verbatim_record_is_never_refusal_validated(client, monkeypatch):
    """The parent may say a condition and a dose. Their words stand."""
    said = "my sugar is high and I took 2 tablets twice a day"
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard(said, language="en-IN"))
    _stub_chat(monkeypatch, reply="Thank you for telling me. I have noted it.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech(text, language="en-IN"))

    r = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma"},
        files={"file": ("note.wav", b"RIFFfake", "audio/wav")},
    )
    assert r.status_code == 200
    # Stored and returned exactly, with no escalation caused by their own words.
    assert r.json()["heard"]["verbatim"] == said
    assert store.utterances()[0].verbatim_text == said


def test_a_typed_message_works_without_audio(client, monkeypatch):
    _stub_chat(monkeypatch, reply="Noted. I am telling Ravi.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech(text))

    r = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_son", "text": "Amma's tablets are nearly over."},
    )
    assert r.status_code == 200
    assert r.json()["heard"]["route"] == "text"


# --- the agent's own words are gated ------------------------------------

def test_a_reply_naming_a_condition_is_discarded_and_handed_off(client, monkeypatch):
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard("అమ్మకి నలత"))
    _stub_chat(monkeypatch, reply="This sounds like her diabetes. Give 2 tablets twice a day.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech(text))

    r = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma"},
        files={"file": ("note.wav", b"RIFFfake", "audio/wav")},
    )
    assert r.status_code == 200
    body = r.json()

    assert body["reply"]["refused_and_replaced"] is True
    # Neither the condition nor the dose survives into what is spoken.
    assert "diabetes" not in body["reply"]["text_en"].lower()
    assert "tablet" not in body["reply"]["text_en"].lower()
    assert "Ravi" in body["reply"]["text_en"]  # handed to the responsible person
    assert any("discarded" in e for e in body["escalations"])
    assert any(e["action"] == "agent_reply_refused" for e in audit.events())


def test_the_discarded_reply_is_still_spoken_so_the_person_is_not_left_in_silence(
    client, monkeypatch
):
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard("ఏదో కష్టంగా ఉంది"))
    _stub_chat(monkeypatch, reply="Take 500 mg now.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech(text))

    body = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma", "speak": "true"},
        files={"file": ("note.wav", b"RIFFfake", "audio/wav")},
    ).json()
    assert body["reply"]["refused_and_replaced"] is True
    assert body["reply"]["spoken"] is True


# --- severity only escalates --------------------------------------------

def test_the_tier_never_drops_across_turns(client, monkeypatch):
    """The mock assessment proposes "elevated" with escalated=true. An episode
    already at "urgent" must not come back below urgent: the ratchet holds it
    there, and the model's own doubt then costs one further step upward."""
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard("ఇంకా అలాగే ఉంది"))
    _stub_chat(monkeypatch, reply="Understood. I am still on it.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech(text))

    from app.api import talk as talk_mod
    from app.assess.tier import index

    talk_mod._episode_tier["ep_fixed"] = "urgent"
    body = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma", "episode_id": "ep_fixed", "text": "still the same"},
    ).json()

    assert index(body["assessment"]["tier"]) >= index("urgent")
    assert "held at the episode's existing tier" in body["assessment"]["ratchet"]
    assert body["assessment"]["escalated"] is True


def test_doubt_costs_one_step_on_top_of_the_model_tier(monkeypatch):
    """The ratchet, directly: the model's own escalation flag means it could not
    tell, and that is worth one step upward on its own."""
    from app.assess.tier import ratchet

    assert ratchet("elevated", previous="urgent", certain=False).tier == "critical"
    assert ratchet("routine", previous=None, certain=True).tier == "routine"


# --- gates --------------------------------------------------------------

def test_unknown_household_is_404(client):
    r = client.post("/agent/talk", data={"household_id": "nope", "person_id": "p_amma", "text": "hi"})
    assert r.status_code == 404


def test_unknown_person_is_404(client):
    r = client.post("/agent/talk", data={"household_id": HH, "person_id": "ghost", "text": "hi"})
    assert r.status_code == 404


def test_a_person_without_consent_is_refused_and_nothing_is_stored(client):
    hh = store.household(HH)
    hh.person("p_sister").consent_given_at = None

    r = client.post("/agent/talk", data={"household_id": HH, "person_id": "p_sister", "text": "hi"})
    assert r.status_code == 403
    assert store.utterances() == []


def test_neither_audio_nor_text_is_400(client):
    r = client.post("/agent/talk", data={"household_id": HH, "person_id": "p_amma"})
    assert r.status_code == 400


def test_empty_audio_is_400(client):
    r = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma"},
        files={"file": ("note.wav", b"", "audio/wav")},
    )
    assert r.status_code == 400


# --- the conversation record --------------------------------------------

def test_the_conversation_keeps_both_speakers_in_order(client, monkeypatch):
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard("అమ్మ బాగా లేదు"))
    _stub_chat(monkeypatch, reply="Thank you. I am telling Ravi now.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech("తెలుగు"))

    ep = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma", "speak": "true"},
        files={"file": ("note.wav", b"RIFFfake", "audio/wav")},
    ).json()["episode_id"]

    turns = client.get(f"/agent/conversation/{ep}").json()["turns"]
    assert [t["speaker"] for t in turns] == ["p_amma", "agent"]
    assert turns[0]["verbatim"] == "అమ్మ బాగా లేదు"


def test_the_language_confidence_floor_flags_a_human_check(client, monkeypatch):
    monkeypatch.setattr(stt, "transcribe", lambda *a, **k: _fake_heard("unclear", probability=0.4))
    _stub_chat(monkeypatch, reply="Thank you, I have noted it.")
    monkeypatch.setattr(tts, "speak", lambda text, lang, **k: _fake_speech(text))

    body = client.post(
        "/agent/talk",
        data={"household_id": HH, "person_id": "p_amma"},
        files={"file": ("note.wav", b"RIFFfake", "audio/wav")},
    ).json()
    assert body["heard"]["needs_human_confirmation"] is True
