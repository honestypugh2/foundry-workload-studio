"""Quality Complaint Triage agent.

Produces a strongly-typed `ComplaintTriageResult`. The default implementation
uses deterministic heuristics so the demo runs offline / in tests; in
production, swap `_heuristic_triage` with a Microsoft Agent Framework call
returning the same Pydantic schema (structured output).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from src.common.models import (
    Complaint,
    ComplaintCategory,
    ComplaintTriageResult,
    Severity,
)

SYSTEM_PROMPT = (
    "You are a quality engineering complaint triage agent. Given a customer "
    "complaint, classify category and severity, summarize the issue in one "
    "sentence, suggest the appropriate routing queue, and flag whether human "
    "escalation is required. Return strict JSON conforming to the supplied "
    "schema. Do NOT invent device IDs or customer data."
)

TriageFn = Callable[[Complaint], ComplaintTriageResult]


# Word-boundary matched terms keyed by category. Order matters for precedence:
# USAGE is evaluated before SOFTWARE so questions like "how do I install..."
# are not misrouted as software defects.
_SAFETY_TERMS = ("injury", "injuries", "burn", "burned", "fire", "smoke", "shock", "hazard")
_HARDWARE_TERMS = ("alarm", "cooling", "coolant", "pump", "leak", "power", "overheat", "pulse", "laser")
_USAGE_TERMS = ("how do i", "how can i", "manual", "training", "setup", "install")
_SOFTWARE_TERMS = ("crash", "freeze", "freezes", "ui", "screen", "firmware", "bug", "error code")

_NEGATED_PATIENT_HARM = re.compile(r"\bno\s+(patient\s+harm|injury|injuries)\b", re.IGNORECASE)
_PATIENT_HARM = re.compile(r"\bpatient\s+harm\b", re.IGNORECASE)


def _has_term(lowered: str, terms: tuple[str, ...]) -> bool:
    for term in terms:
        if " " in term:
            if term in lowered:
                return True
        elif re.search(rf"\b{re.escape(term)}\b", lowered):
            return True
    return False


def _categorize(text: str) -> ComplaintCategory:
    lowered = text.lower()
    if _PATIENT_HARM.search(lowered) and not _NEGATED_PATIENT_HARM.search(lowered):
        return ComplaintCategory.SAFETY
    if _has_term(lowered, _SAFETY_TERMS):
        return ComplaintCategory.SAFETY
    if _has_term(lowered, _USAGE_TERMS):
        return ComplaintCategory.USAGE
    if _has_term(lowered, _HARDWARE_TERMS):
        return ComplaintCategory.HARDWARE
    if _has_term(lowered, _SOFTWARE_TERMS):
        return ComplaintCategory.SOFTWARE
    return ComplaintCategory.OTHER


def _severity(category: ComplaintCategory, text: str) -> Severity:
    lowered = text.lower()
    has_patient_harm = bool(
        _PATIENT_HARM.search(lowered) and not _NEGATED_PATIENT_HARM.search(lowered)
    )
    if category is ComplaintCategory.SAFETY or has_patient_harm:
        return Severity.CRITICAL
    if category is ComplaintCategory.HARDWARE and any(
        w in lowered for w in ("alarm", "overheat", "leak", "smoke", "fire")
    ):
        return Severity.HIGH
    if category is ComplaintCategory.SOFTWARE and any(w in lowered for w in ("crash", "freeze")):
        return Severity.MEDIUM
    return Severity.LOW


def _route(category: ComplaintCategory, severity: Severity) -> str:
    if severity is Severity.CRITICAL:
        return "regulatory-affairs"
    return {
        ComplaintCategory.HARDWARE: "field-service",
        ComplaintCategory.SOFTWARE: "engineering-support",
        ComplaintCategory.SAFETY: "regulatory-affairs",
        ComplaintCategory.USAGE: "customer-success",
        ComplaintCategory.OTHER: "triage-queue",
    }[category]


_DEVICE_UNIT_RE = re.compile(r"\b(DEV-\d{2,})\b")
_DEVICE_MODEL_RE = re.compile(r"\b([A-Z]{2,}-\d{2,})\b")


def _extract_entities(text: str) -> dict[str, str]:
    """Prefer concrete device unit IDs (DEV-xxxx); fall back to model identifiers."""
    out: dict[str, str] = {}
    unit = _DEVICE_UNIT_RE.search(text)
    if unit:
        out["device_id"] = unit.group(1)
        return out
    model = _DEVICE_MODEL_RE.search(text)
    if model:
        out["device_id"] = model.group(1)
    return out


def _heuristic_triage(complaint: Complaint) -> ComplaintTriageResult:
    text = complaint.description
    category = _categorize(text)
    severity = _severity(category, text)
    summary = text.strip().split(". ")[0][:480]
    return ComplaintTriageResult(
        complaint_id=complaint.complaint_id,
        category=category,
        severity=severity,
        summary=summary,
        suggested_route=_route(category, severity),
        requires_escalation=severity in {Severity.HIGH, Severity.CRITICAL},
        extracted_entities=_extract_entities(text),
    )


def triage(complaint: Complaint, *, agent: TriageFn | None = None) -> ComplaintTriageResult:
    """Run triage. Pass `agent=` to inject an Agent Framework-backed implementation."""
    return (agent or _default_agent())(complaint)


def _default_agent() -> TriageFn:
    """Return a Foundry-backed triage when configured; otherwise heuristic."""
    from src.common.foundry_agents import is_foundry_configured

    if is_foundry_configured():
        return _foundry_triage
    return _heuristic_triage


def _foundry_triage(complaint: Complaint) -> ComplaintTriageResult:
    """Foundry persistent-agent triage with JSON response_format.

    Falls back to heuristic on any failure so the demo never breaks.
    """
    import json

    from src.common.foundry_agents import run_agent

    prompt = (
        "Classify the following device complaint. Return ONLY JSON with keys: "
        "category (one of hardware/software/usage/safety/other), severity "
        "(low/medium/high/critical), summary (string), suggested_route (string), "
        "requires_escalation (bool), extracted_entities (object).\n\n"
        f"complaint_id: {complaint.complaint_id}\n"
        f"description: {complaint.description}"
    )
    try:
        text = run_agent("quality_complaint_triage", prompt)
        data = json.loads(text)
        return ComplaintTriageResult(complaint_id=complaint.complaint_id, **data)
    except Exception:  # fall back deterministically
        return _heuristic_triage(complaint)
