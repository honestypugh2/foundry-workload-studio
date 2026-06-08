"""Lightweight content safety + grounding helpers.

For production, route flagged content through Azure AI Content Safety. This
module provides a deterministic local pre-filter so APIs/tests can run offline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns deliberately conservative; they handle the most common abuse vectors
# while remaining cheap and side-effect free for unit tests.
_BLOCKLIST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(ssn|social\s+security)\b\s*[:#]?\s*\d{3}-?\d{2}-?\d{4}", re.IGNORECASE),
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"\bsystem\s*prompt\s*[:=]", re.IGNORECASE),
)

_PHI_HINTS = ("patient name", "medical record number", "mrn:")


@dataclass(frozen=True, slots=True)
class ContentSafetyVerdict:
    allowed: bool
    reasons: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ContentSafetyVerdict:
        return cls(allowed=True)


def check_safety(text: str) -> ContentSafetyVerdict:
    """Run cheap deterministic checks. Returns an `allowed=False` verdict on hit."""
    if not text or not text.strip():
        return ContentSafetyVerdict(allowed=False, reasons=("empty_input",))

    reasons: list[str] = []
    for pat in _BLOCKLIST_PATTERNS:
        if pat.search(text):
            reasons.append(f"blocked_pattern:{pat.pattern[:40]}")
    lowered = text.lower()
    for hint in _PHI_HINTS:
        if hint in lowered:
            reasons.append(f"possible_phi:{hint}")

    if reasons:
        return ContentSafetyVerdict(allowed=False, reasons=tuple(reasons))
    return ContentSafetyVerdict.ok()
