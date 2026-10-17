"""Mayura / Sarvam-Translate wrapper (prompt.md section 7, "Checking in").

`translate_text` is the one function other modules call: English text in, a
BCP-47 target language code in, translated text out. It picks `mayura:v1` for
Mayura's 11 languages and `sarvam-translate:v1` otherwise, honours each
model's character cap by chunking on sentence boundaries (never silently
truncating), and applies a Roman `output_script` only where Mayura supports
it. It does not import anything from `notify/` or `api/` — `app/notify/talk`
and the clinic-call agent call it directly, same as `app/api/notify.py` does.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .client import client, live, with_retries

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

# README "Component deep-dives / Mayura": 11 languages (10 Indian + English).
MAYURA_LANGUAGES = {
    "hi-IN", "bn-IN", "gu-IN", "kn-IN", "ml-IN", "mr-IN",
    "od-IN", "pa-IN", "ta-IN", "te-IN", "en-IN",
}
MAYURA_CHAR_LIMIT = 1000
SARVAM_TRANSLATE_CHAR_LIMIT = 2000


class TranslateTextTooLong(Exception):
    """A single sentence alone exceeds the active model's character cap.

    Raised instead of silently truncating it (BRIEF rule: chunk or refuse
    explicitly).
    """


@dataclass(frozen=True)
class TranslateResult:
    text: str
    model: str
    source_language_code: str
    output_script_applied: bool
    source: str  # "sarvam" | "mock"


def _model_for(target_language_code: str) -> str:
    return "mayura:v1" if target_language_code in MAYURA_LANGUAGES else "sarvam-translate:v1"


def _char_limit(model: str) -> int:
    return MAYURA_CHAR_LIMIT if model == "mayura:v1" else SARVAM_TRANSLATE_CHAR_LIMIT


def _chunk(text: str, limit: int) -> list[str]:
    """Greedily pack sentences into chunks <= limit. Raises if one sentence
    alone is already over the limit, rather than cutting it mid-word."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > limit:
            raise TranslateTextTooLong(
                f"a single sentence is {len(sentence)} chars, over the {limit}-char cap"
            )
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _mock_response() -> dict:
    return json.loads((FIXTURES / "translate_sample.json").read_text())


def _translate_chunk(
    chunk: str,
    *,
    target_language_code: str,
    source_language_code: str,
    model: str,
    output_script: str | None,
) -> tuple[str, str, bool]:
    """One Sarvam call (or its mock stand-in). Returns (translated_text,
    detected_source_language, output_script_applied)."""
    if not live():
        raw = _mock_response()
        # DECISION: mock mode returns the one recorded sample verbatim. It is
        # not a real translation of `chunk` — the caller tags source="mock"
        # from this result, so it can never be mistaken for a live call.
        return raw["translated_text"], raw.get("source_language_code", source_language_code), False

    kwargs: dict = {
        "input": chunk,
        "source_language_code": source_language_code,
        "target_language_code": target_language_code,
        "model": model,
    }
    applied = False
    if model == "mayura:v1":
        kwargs["mode"] = "modern-colloquial"
        if output_script:
            kwargs["output_script"] = output_script
            applied = True
    # BRIEF rule: never pass output_script or numerals_format to sarvam-translate:v1.

    def _call():
        return client().text.translate(**kwargs)

    response = with_retries(_call)
    return response.translated_text, response.source_language_code, applied


def translate_text(
    text: str,
    target_language_code: str,
    *,
    source_language_code: str = "en-IN",
    output_script: str | None = None,
) -> TranslateResult:
    """Translate agent-authored text for one recipient's language.

    Picks `mayura:v1` (Mayura's 11 languages) or `sarvam-translate:v1`
    (everything else) and chunks on sentence boundaries to respect whichever
    model's character cap applies. `output_script="roman"` is honoured only
    on `mayura:v1`; passed against `sarvam-translate:v1` it is silently
    dropped (that model does not take it — BRIEF rule), and
    `output_script_applied` on the result says so.

    Does not skip the call for `target_language_code == "en-IN"` itself —
    callers that already have English text should not call this at all.
    """
    model = _model_for(target_language_code)
    limit = _char_limit(model)
    chunks = _chunk(text, limit)
    if not chunks:
        return TranslateResult(
            text="",
            model=model,
            source_language_code=source_language_code,
            output_script_applied=False,
            source="sarvam" if live() else "mock",
        )

    parts: list[str] = []
    detected_source = source_language_code
    applied = False
    for chunk in chunks:
        translated, detected_source, applied = _translate_chunk(
            chunk,
            target_language_code=target_language_code,
            source_language_code=source_language_code,
            model=model,
            output_script=output_script,
        )
        parts.append(translated)

    return TranslateResult(
        text=" ".join(parts),
        model=model,
        source_language_code=detected_source,
        output_script_applied=applied,
        source="sarvam" if live() else "mock",
    )
