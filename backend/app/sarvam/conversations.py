"""`sarvam-105b-conversations` (README "System prompt skeleton for the
live-call agent"; prompt.md section 9 voice agents).

The real-time variant of sarvam-105b that runs inside a live voice-agent
call: 32K context, one turn in (the system prompt plus the dialogue so far),
one agent line out. Reasoning is on by default here too (same model family
as `sarvam-105b`), so `max_tokens` is kept well clear of the reasoning
budget, matching app/sarvam/chat.py.

Rule 2: every line this produces is agent-authored and must pass
`app.assess.refusal.enforce()` before anyone on the call hears it — this
module only produces candidate text, it never gates its own output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .client import client, live, with_retries

MODEL = "sarvam-105b-conversations"
MAX_TOKENS = 1024  # 32K context; a live-call turn is a sentence or two.

# DECISION: mock mode returns a canned, already-safe line instead of calling
# the model, so a demo without a key never risks a mock turn that looks like
# a live-model mistake (same reasoning as chat.py's _MOCK_COMPLETION).
_MOCK_TURN = "Mock sarvam-105b-conversations reply (no live call made)."


@dataclass
class ConversationTurn:
    text: str
    source: Literal["sarvam", "mock"]


def next_turn(
    messages: list[dict[str, str]], *, max_tokens: int = MAX_TOKENS
) -> ConversationTurn:
    """One agent turn in a live-call dialogue.

    `messages` is the running transcript so far — a leading `system` message
    (the README skeleton plus the call's goal), then alternating `user`
    (what the other party on the call just said) and `assistant` (the
    agent's own prior lines). Returns the agent's next line as candidate
    text — unvalidated; the caller must run it through
    `app.assess.refusal.enforce()` before it is spoken or stored.
    """
    if not live():
        return ConversationTurn(text=_MOCK_TURN, source="mock")

    def _call():
        return client().chat.completions(
            model=MODEL, messages=messages, max_tokens=max_tokens
        )

    resp = with_retries(_call)
    text = (resp.choices[0].message.content or "").strip()
    return ConversationTurn(text=text, source="sarvam")
