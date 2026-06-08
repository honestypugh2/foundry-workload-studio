"""Tests for the Quality Complaint Triage agent."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.common.models import (
    Complaint,
    ComplaintCategory,
    Severity,
)
from src.quality_complaint_triage.agent import triage
from src.quality_complaint_triage.api import create_app


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pdf_example_complaint_triages_as_hardware_high(complaints_path: Path) -> None:
    rows = _load(complaints_path)
    target = next(r for r in rows if r["complaint_id"] == "CMP-001")
    result = triage(Complaint.model_validate(target))
    assert result.category is ComplaintCategory.HARDWARE
    assert result.severity is Severity.HIGH
    assert result.requires_escalation is True
    assert result.suggested_route == "field-service"


def test_safety_complaint_triages_as_critical(complaints_path: Path) -> None:
    rows = _load(complaints_path)
    target = next(r for r in rows if r["complaint_id"] == "CMP-005")
    result = triage(Complaint.model_validate(target))
    assert result.severity is Severity.CRITICAL
    assert result.suggested_route == "regulatory-affairs"
    assert result.extracted_entities.get("device_id") == "DEV-4421"


def test_software_freeze_triages_as_software_medium(complaints_path: Path) -> None:
    rows = _load(complaints_path)
    target = next(r for r in rows if r["complaint_id"] == "CMP-002")
    result = triage(Complaint.model_validate(target))
    assert result.category is ComplaintCategory.SOFTWARE
    assert result.severity is Severity.MEDIUM


def test_usage_complaint_triages_as_low(complaints_path: Path) -> None:
    rows = _load(complaints_path)
    target = next(r for r in rows if r["complaint_id"] == "CMP-004")
    result = triage(Complaint.model_validate(target))
    assert result.category is ComplaintCategory.USAGE
    assert result.severity is Severity.LOW
    assert result.requires_escalation is False


def test_triage_endpoint() -> None:
    client = TestClient(create_app())
    payload = {
        "complaint_id": "T-1",
        "description": "Cooling alarm fires repeatedly during use on device LX-200.",
    }
    r = client.post("/triage", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == "hardware"
    assert body["severity"] in {"high", "medium"}
