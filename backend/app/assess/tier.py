"""The tier ratchet. Severity only escalates (prompt.md rule 3).

No function here can return a tier below the one it was given. The only
movement available to the agent on doubt is upward, and upward means a human is
asked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["routine", "elevated", "urgent", "critical"]

# Ordered, lowest first. The index is the severity.
TIERS: tuple[Tier, ...] = ("routine", "elevated", "urgent", "critical")


class UnknownTier(ValueError):
    pass


def index(tier: str) -> int:
    try:
        return TIERS.index(tier)  # type: ignore[arg-type]
    except ValueError as exc:
        raise UnknownTier(f"{tier!r} is not one of {TIERS}") from exc


@dataclass(frozen=True)
class TierDecision:
    tier: Tier
    escalated: bool
    reason: str


def ratchet(
    proposed: str,
    *,
    previous: str | None = None,
    certain: bool = True,
    model_escalated: bool = False,
) -> TierDecision:
    """Combine the model's tier with the episode's current tier.

    `certain=False` means the four factors disagreed or the agent could not
    tell. That costs one step upward and asks a human — it never resolves
    downward, and never silently.
    """
    i = index(proposed)
    notes: list[str] = []

    if previous is not None:
        j = index(previous)
        if j > i:
            notes.append(f"held at the episode's existing tier {previous!r}")
            i = j

    escalated = bool(model_escalated)
    if model_escalated:
        notes.append("the model asked for a human")

    if not certain:
        if i < len(TIERS) - 1:
            i += 1
            notes.append("raised one step because the agent could not tell")
        else:
            notes.append("already at the top tier and the agent could not tell")
        escalated = True

    tier = TIERS[i]
    if tier == "critical":
        # A critical tier always reaches a human, whatever the model said.
        escalated = True
        notes.append("critical tier always reaches a human")

    if not notes:
        notes.append("the model's tier stood")

    return TierDecision(tier=tier, escalated=escalated, reason="; ".join(notes))
