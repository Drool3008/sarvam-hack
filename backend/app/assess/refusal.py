"""The refusal validator (prompt.md section 8, deterministic layer).

Rule 2 is an invariant, not a feature: no model output that reaches a person may
name a condition, suggest a dose, or substitute a medicine. Both functionalities
in this build put model text in front of a human, so both pass through here
first. A violation discards the output and escalates.

Only the deterministic layer is implemented in this slice. The second
`sarvam-105b` boolean model check from section 8 sits behind the same
`validate()` signature and is marked OPEN below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Numbers glued to a unit, or a frequency: "500 mg", "5ml", "2 tablets",
# "twice a day", "3 times a day", "1-0-1".
_DOSE_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu|units?)\b", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:tablets?|tabs?|caps?|capsules?|drops?|spoons?|tsp)\b", re.I),
    re.compile(r"\b(?:once|twice|thrice|\d+)\s*(?:times?\s*)?(?:a|per|each)\s*(?:day|night|week)\b", re.I),
    re.compile(r"\b\d\s*-\s*\d\s*-\s*\d\b"),
]

# A small condition lexicon. The household's own condition labels are added per
# call, because a label is stored as the family entered it and must never be
# spoken back by the agent.
_CONDITION_LEXICON = {
    "diabetes", "diabetic", "hypertension", "high blood pressure", "bp high",
    "asthma", "copd", "cancer", "tumour", "tumor", "stroke", "heart attack",
    "cardiac arrest", "kidney failure", "renal failure", "dengue", "malaria",
    "typhoid", "tuberculosis", "tb", "covid", "pneumonia", "arthritis",
    "thyroid", "hypothyroid", "hyperthyroid", "anaemia", "anemia", "epilepsy",
    "depression", "dementia", "alzheimer", "parkinson", "jaundice", "hepatitis",
    "ulcer", "migraine", "sepsis",
}


@dataclass(frozen=True)
class RefusalVerdict:
    ok: bool
    violations: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.ok


class RefusalViolation(Exception):
    """Raised when agent-authored text breaks one of the three refusals."""

    def __init__(self, verdict: RefusalVerdict):
        self.verdict = verdict
        super().__init__("; ".join(verdict.violations))


def _word_hit(text_lower: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", text_lower) is not None


def validate(
    text: str,
    *,
    condition_labels: list[str] | None = None,
    prescribed_medicines: list[str] | None = None,
    candidate_medicines: list[str] | None = None,
) -> RefusalVerdict:
    """Check agent-authored text against the three refusals.

    `candidate_medicines` is the list of medicine names the text is allowed to
    mention — anything named that is not already prescribed for this person is a
    substitution. Pass the household's prescribed names as `prescribed_medicines`
    and the names actually detected (or asserted) as `candidate_medicines`.
    """
    # OPEN: the second layer is a strict-boolean `sarvam-105b` call
    # (names_a_condition / suggests_a_dose / suggests_a_substitute). It belongs
    # behind this same signature once the chat wrapper lands.
    lower = text.lower()
    violations: list[str] = []

    for pattern in _DOSE_PATTERNS:
        hit = pattern.search(text)
        if hit:
            violations.append(f"suggests a dose: {hit.group(0)!r}")
            break

    labels = [c for c in (condition_labels or []) if c.strip()]
    for term in sorted(_CONDITION_LEXICON | {c.lower() for c in labels}):
        if _word_hit(lower, term):
            violations.append(f"names a condition: {term!r}")
            break

    allowed = {m.lower() for m in (prescribed_medicines or [])}
    for name in candidate_medicines or []:
        if name and name.lower() not in allowed:
            violations.append(f"substitutes a medicine: {name!r}")
            break

    return RefusalVerdict(ok=not violations, violations=tuple(violations))


def enforce(text: str, **kw) -> str:
    """Return `text` if it passes, else raise. Callers turn this into an escalation."""
    verdict = validate(text, **kw)
    if not verdict:
        raise RefusalViolation(verdict)
    return text
