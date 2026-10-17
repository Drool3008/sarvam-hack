"""Bulbul v4 Flash wrapper (prompt.md section 7, README "Checking in").

`speak` is the one function other modules call: source text (default
English) and the recipient's language code in, a playable WAV path out. The
Bulbul v4 Flash coverage check and the `second_language` fallback live in
here, not in the caller — README's language-coverage table: v4 Flash speaks
10 languages (hi, en, en-hi, bn, gu, kn, mr, pa, ta, te), not Malayalam or
Odia, which are v3-only. `app/api/notify.py`, the conversation-turn
orchestrator and the clinic-call agent all call `speak` directly; none of
them need to know about that gap.

Speaking in a non-English language re-translates the source text through
`translate_text` first (Bulbul takes native script only, no SSML) — so a
`speak` call can cost two Sarvam calls, not one. That is a deliberate trade
for letting every caller hand this function raw English and a language code
and get back correct audio, including in the fallback case, without having to
pre-translate for whichever language Bulbul ends up actually using.
"""

from __future__ import annotations

import base64
import os
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from .client import client, live, with_retries
from .translate import translate_text

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
# Where rendered WAVs land. Overridable because serverless hosts (Vercel,
# Cloud Run) give a read-only filesystem apart from /tmp. The returned
# `audio_ref` keeps its stable "out/<name>" shape whatever the directory is;
# the app serves that prefix from this directory.
OUT_DIR = Path(os.environ.get("AUDIO_DIR") or Path(__file__).resolve().parents[3] / "out")

# README language-coverage table + "Component deep-dives / Bulbul": v4 Flash
# speaks 10 languages. Not ml-IN or od-IN (v3-only, v3 end-of-life on Voice
# Agents 2026-11-10) and not any of the other 22-language Saaras/Mayura set.
BULBUL_V4_FLASH_LANGUAGES = {
    "hi-IN", "en-IN", "en-hi", "bn-IN", "gu-IN",
    "kn-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN",
}
TTS_CHAR_LIMIT = 2500


class SpeechTextTooLong(Exception):
    """Native-script text exceeds Bulbul's 2,500-character cap. Refused, not truncated."""


@dataclass(frozen=True)
class SpeechResult:
    audio_ref: str | None  # path under out/, relative to the repo root; None if not spoken
    spoken_language: str | None  # the language actually spoken (may be the fallback)
    fallback_reason: str | None  # set when second_language was used, or neither language is covered
    spoken: bool
    source: str  # "sarvam" | "mock"
    model: str = "bulbul:v4-flash"
    text: str | None = None  # the native-script text actually sent to Bulbul


def _mock_response() -> dict:
    return json.loads((FIXTURES / "tts_sample.json").read_text())


def _write_wav(audio_b64: str) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}.wav"
    (OUT_DIR / name).write_bytes(base64.b64decode(audio_b64))
    return f"out/{name}"


def _synthesize(text: str, language_code: str, *, pace: float, dict_id: str | None) -> tuple[str, str]:
    """One Sarvam call (or its mock stand-in). Returns (audio_ref, source)."""
    if not live():
        raw = _mock_response()
        # DECISION: mock mode writes the one recorded sample WAV verbatim —
        # not real audio of `text` — tagged source="mock" by the caller.
        return _write_wav(raw["audios"][0]), "mock"

    kwargs: dict = {
        "text": text,
        "language_code": language_code,
        "model": "bulbul:v4-flash",
        "pace": pace,
    }
    if dict_id:
        kwargs["dict_id"] = dict_id

    def _call():
        return client().text_to_speech.convert(**kwargs)

    response = with_retries(_call)
    return _write_wav(response.audios[0]), "sarvam"


def speak(
    text: str,
    language_code: str,
    *,
    source_language_code: str = "en-IN",
    second_language: str | None = None,
    pace: float = 0.8,
    dict_id: str | None = None,
) -> SpeechResult:
    """Speak `text` (given in `source_language_code`) for someone whose
    preferred language is `language_code`.

    Resolves Bulbul v4 Flash's coverage gap itself: if `language_code` is not
    one of `BULBUL_V4_FLASH_LANGUAGES`, falls back to `second_language` when
    that is covered, and says so via `fallback_reason`. If neither is
    covered, returns `spoken=False` with a reason instead of speaking the
    wrong language.
    """
    if language_code in BULBUL_V4_FLASH_LANGUAGES:
        speak_lang, fallback_reason = language_code, None
    elif second_language and second_language in BULBUL_V4_FLASH_LANGUAGES:
        speak_lang = second_language
        fallback_reason = (
            f"{language_code} is not covered by bulbul:v4-flash; "
            f"speaking in second_language {second_language} instead"
        )
    else:
        return SpeechResult(
            audio_ref=None,
            spoken_language=None,
            fallback_reason=(
                f"neither {language_code} nor second_language ({second_language!r}) "
                "is covered by bulbul:v4-flash"
            ),
            spoken=False,
            source="sarvam" if live() else "mock",
        )

    if speak_lang == source_language_code:
        native_text, translate_source = text, None
    else:
        translated = translate_text(text, speak_lang, source_language_code=source_language_code)
        native_text, translate_source = translated.text, translated.source

    if len(native_text) > TTS_CHAR_LIMIT:
        raise SpeechTextTooLong(f"{len(native_text)} chars, over the {TTS_CHAR_LIMIT}-char cap")

    audio_ref, tts_source = _synthesize(native_text, speak_lang, pace=pace, dict_id=dict_id)
    combined_source = "mock" if "mock" in (translate_source, tts_source) else "sarvam"

    return SpeechResult(
        audio_ref=audio_ref,
        spoken_language=speak_lang,
        fallback_reason=fallback_reason,
        spoken=True,
        source=combined_source,
        text=native_text,
    )
