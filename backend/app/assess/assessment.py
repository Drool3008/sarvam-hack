"""The Assess stage: four factors, one tier, one reason, escalate on doubt.

The `response_format` below is the README's assessment schema, unchanged and
`strict`, so the model returns that shape or nothing. `factors_used` may contain
only the four factors — the enum enforces it rather than a later check.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..domain import Household, Person
from ..sarvam import chat
from .tier import TierDecision, ratchet

FACTORS = (
    "matches_red_flag_list",
    "new_or_worsening",
    "touches_existing_medicine",
    "context_time_distance_reachability_money",
)

ASSESSMENT_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "assessment",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "trigger_kind": {
                    "type": "string",
                    "enum": ["affected_person", "family_member", "agent_clock"],
                },
                "source": {"type": "string"},
                "tier": {
                    "type": "string",
                    "enum": ["routine", "elevated", "urgent", "critical"],
                },
                "factors_used": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(FACTORS)},
                },
                "reason": {"type": "string"},
                "escalated": {"type": "boolean"},
                "account_type": {"type": "string", "enum": ["firsthand", "secondhand"]},
                "verbatim_transcript_ref": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": [
                "trigger_kind",
                "source",
                "tier",
                "factors_used",
                "reason",
                "escalated",
                "account_type",
                "verbatim_transcript_ref",
                "summary",
            ],
            "additionalProperties": False,
        },
    },
}

ASSESS_SYSTEM = """You assess what a family member has just reported about an
ageing parent's health, for a household agent.

You do not diagnose. You never name a condition, never state a dose, and never
suggest a different medicine. The conditions and medicines you are given are for
MATCHING ONLY — to notice that a report touches something already known. Do not
repeat a condition name in your `reason` or `summary`.

Weigh exactly four factors. List in `factors_used` ONLY the factors that
actually carried your decision — a factor you checked and found false, or could
not determine, is NOT a used factor and must be left out. Do not list all four
out of completeness. If you could not determine a factor, say so in `reason` and
set `escalated` to true rather than citing it.

The four factors are:
- matches_red_flag_list: what was said matches the household's red-flag list.
- new_or_worsening: this is new for this person, or worse than before.
- touches_existing_medicine: it concerns a medicine they already take.
- context_time_distance_reachability_money: the hour, the distance, who is
  reachable, and what is left in the wallet.

Give one line of reasoning. If the factors disagree, or you cannot tell, set
`escalated` to true and choose the HIGHER tier. Never guess downward.

`reason` is one line. It must be consistent with `factors_used`: do not name a
factor in `reason` as false or unknown and also list it in `factors_used`.

`summary` is one or two sentences of plain English for the record. It must
contain no condition name and no dose."""

# DECISION: a mock assessment has to be schema-valid JSON, so the canned value
# is a conservative one — escalated, and no tier claimed below "elevated".
_MOCK_ASSESSMENT = json.dumps(
    {
        "trigger_kind": "affected_person",
        "source": "mock",
        "tier": "elevated",
        "factors_used": ["new_or_worsening"],
        "reason": "Recorded fixture response; no model was called.",
        "escalated": True,
        "account_type": "firsthand",
        "verbatim_transcript_ref": "",
        "summary": "A family member reported something that a person should review.",
    }
)


class AssessmentFailed(Exception):
    """The model did not return usable JSON in the strict shape."""


@dataclass
class Assessment:
    trigger_kind: str
    source_label: str
    tier: str
    factors_used: list[str]
    reason: str
    escalated: bool
    account_type: str
    verbatim_transcript_ref: str
    summary: str
    decision: TierDecision
    sarvam_source: str
    raw: dict[str, Any]


def _context_block(household: Household, speaker: Person, affected: Person | None) -> str:
    prescribed = [
        f"{m.name} {m.strength}".strip()
        for m in household.medicines
        if affected is None or m.person_id == affected.id
    ]
    return "\n".join(
        [
            f"Household: {household.id}, city pair {household.city_pair[0]} / {household.city_pair[1]}.",
            f"Who is speaking: {speaker.name}, roles {sorted(speaker.roles)}, language {speaker.preferred_language}.",
            f"Affected person: {affected.name if affected else 'unknown'}.",
            f"Known conditions (for matching only, never to repeat): {household.condition_labels}.",
            f"Prescribed medicines (for matching only): {prescribed}.",
            f"Household red-flag list: {household.red_flags}.",
        ]
    )


def assess(
    *,
    household: Household,
    speaker: Person,
    verbatim_text: str,
    verbatim_ref: str,
    trigger_kind: str,
    previous_tier: str | None = None,
) -> Assessment:
    """One strict-schema `sarvam-105b` call, then the tier ratchet on top of it."""
    affected = household.affected_person()
    account_type = "firsthand" if affected and speaker.id == affected.id else "secondhand"

    messages = [
        {"role": "system", "content": ASSESS_SYSTEM},
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    _context_block(household, speaker, affected),
                    f"Trigger kind: {trigger_kind}.",
                    f"Account type: {account_type}.",
                    f"Verbatim transcript reference: {verbatim_ref}.",
                    f"What was said, word for word:\n{verbatim_text}",
                ]
            ),
        },
    ]

    result = chat.complete(
        messages,
        max_tokens=8192,  # reasoning tokens count toward this
        response_format=ASSESSMENT_RESPONSE_FORMAT,
        reasoning_effort="high",
        mock_text=_MOCK_ASSESSMENT,
    )

    try:
        raw = json.loads(result.text)
    except json.JSONDecodeError as exc:
        raise AssessmentFailed(f"assessment was not JSON: {result.text[:200]!r}") from exc

    missing = [k for k in ASSESSMENT_RESPONSE_FORMAT["json_schema"]["schema"]["required"] if k not in raw]
    if missing:
        raise AssessmentFailed(f"assessment missing fields: {missing}")

    stray = [f for f in raw["factors_used"] if f not in FACTORS]
    if stray:
        raise AssessmentFailed(f"assessment cited factors the product does not use: {stray}")

    # The model's own escalation flag, plus doubt inferred from the factors
    # disagreeing, both feed the ratchet. The ratchet is the only thing that
    # decides the final tier.
    decision = ratchet(
        raw["tier"],
        previous=previous_tier,
        certain=not raw["escalated"],
        model_escalated=bool(raw["escalated"]),
    )

    return Assessment(
        trigger_kind=raw["trigger_kind"],
        source_label=raw["source"],
        tier=decision.tier,
        factors_used=list(raw["factors_used"]),
        reason=raw["reason"],
        escalated=decision.escalated,
        account_type=account_type,  # taken from who actually spoke, not the model
        verbatim_transcript_ref=verbatim_ref,
        summary=raw["summary"],
        decision=decision,
        sarvam_source=result.source,
        raw=raw,
    )
