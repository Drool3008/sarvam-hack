"""`sarvam-105b` chat completions (prompt.md section 7, one function per call).

`complete()` is the reusable primitive — any caller with its own `messages`
and `max_tokens` (the voice-note summary below, or a live conversation-turn
orchestrator) can call it directly. `summarize()` is a convenience wrapper
over `complete()` for the voice-note English summary specifically.

Rule 2: this text is agent-authored, so the caller must run it through
`app.assess.refusal.validate()` / `enforce()` before anyone sees it — this
module only produces candidate text, it never gates its own output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .client import client, live, with_retries

MODEL = "sarvam-105b"
# Reasoning is on by default and reasoning tokens count toward max_tokens, so
# this is kept well clear of a plausible reasoning budget rather than left low.
MAX_TOKENS = 4096

SYSTEM_PROMPT = (
    "You summarise, in at most two sentences of plain English, what a family "
    "member reported in a voice note about a relative's health, for a family "
    "caregiver to read. You must never break these rules: never name or imply "
    "a medical condition or diagnosis; never state, suggest or imply a dose, "
    "frequency or quantity of any medicine; never name a medicine unless it is "
    "explicitly in the 'prescribed medicines' list you are given. Give no "
    "advice, reassurance or next steps — report only that something was said, "
    "in neutral terms."
)

# DECISION: mock mode returns a canned, already-safe summary instead of
# calling sarvam-105b, so a demo without a key never risks producing a
# refusal violation that would look like a live-model mistake.
_MOCK_SUMMARY = (
    "The family reported a voice note from the affected person describing how "
    "they are feeling today."
)

# A generic mock reply for complete(), used by any caller that isn't the
# voice-note summary above (which has its own, context-appropriate canned text).
_MOCK_COMPLETION = "Mock sarvam-105b response (no live call made)."


@dataclass
class ChatResult:
    text: str
    source: Literal["sarvam", "mock"]


@dataclass
class SummaryResult:
    text: str
    source: Literal["sarvam", "mock"]


def complete(
    messages: list[dict[str, str]], *, max_tokens: int = MAX_TOKENS, model: str = MODEL
) -> ChatResult:
    """`chat.completions` with a caller-supplied `messages` list.

    `max_tokens` must stay well above the reasoning budget — reasoning is on
    by default for sarvam-105b and reasoning tokens count against it.
    """
    if not live():
        return ChatResult(text=_MOCK_COMPLETION, source="mock")

    def _call():
        return client().chat.completions(model=model, messages=messages, max_tokens=max_tokens)

    resp = with_retries(_call)
    text = (resp.choices[0].message.content or "").strip()
    return ChatResult(text=text, source="sarvam")


def summarize(verbatim_text: str, *, prescribed_medicines: list[str]) -> SummaryResult:
    """Candidate English summary of `verbatim_text`. Not validated here — the
    caller must run app.assess.refusal.validate()/enforce() before storing or
    returning it.
    """
    if not live():
        return SummaryResult(text=_MOCK_SUMMARY, source="mock")

    medicines_note = (
        "Medicines already prescribed to this person (for your reference only "
        "— never name any medicine not on this list): " + ", ".join(prescribed_medicines)
        if prescribed_medicines
        else "No medicines are on record for this person — do not name any medicine."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": medicines_note},
        {
            "role": "user",
            "content": (
                "Voice note transcript (verbatim, possibly in an Indian "
                f"language — summarise in English): {verbatim_text}"
            ),
        },
    ]
    result = complete(messages, max_tokens=MAX_TOKENS)
    return SummaryResult(text=result.text, source=result.source)
