"""End-to-end smoke for the Quality Complaint Triage agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from scripts.debug import (
    StepResult,
    kv,
    log_triage,
    print_summary,
    run_step,
    section,
)
from src.common.models import (
    Complaint,
    ComplaintCategory,
    Severity,
)
from src.quality_complaint_triage.agent import triage
from src.quality_complaint_triage.api import create_app

COMPLAINTS_PATH = Path(__file__).resolve().parents[1] / "data" / "complaints" / "sample_complaints.json"


def _load_by_id(complaint_id: str) -> Complaint:
    rows = json.loads(COMPLAINTS_PATH.read_text(encoding="utf-8"))
    target = next(r for r in rows if r["complaint_id"] == complaint_id)
    return Complaint.model_validate(target)


def main() -> int:
    results: list[StepResult] = []

    with section("Quality Complaint Triage — direct agent"):

        def case_pdf_example() -> None:
            c = _load_by_id("CMP-001")
            kv("input_complaint", c.description)
            r = triage(c)
            log_triage(r)
            assert r.category is ComplaintCategory.HARDWARE
            assert r.severity is Severity.HIGH
            assert r.requires_escalation is True
            assert r.suggested_route == "field-service"

        def case_safety_critical() -> None:
            c = _load_by_id("CMP-005")
            r = triage(c)
            log_triage(r)
            assert r.severity is Severity.CRITICAL
            assert r.suggested_route == "regulatory-affairs"
            assert r.extracted_entities.get("device_id") == "DEV-4421"

        def case_software_freeze() -> None:
            c = _load_by_id("CMP-002")
            r = triage(c)
            log_triage(r)
            assert r.category is ComplaintCategory.SOFTWARE

        def case_usage_low() -> None:
            c = _load_by_id("CMP-004")
            r = triage(c)
            log_triage(r)
            assert r.category is ComplaintCategory.USAGE
            assert r.severity is Severity.LOW
            assert r.requires_escalation is False

        results.append(run_step("PDF example → hardware/high", case_pdf_example))
        results.append(run_step("Safety complaint → critical", case_safety_critical))
        results.append(run_step("Software freeze classified", case_software_freeze))
        results.append(run_step("Usage question → low/no-escalation", case_usage_low))

    with section("Quality Complaint Triage — FastAPI /triage"):
        client = TestClient(create_app())

        def case_endpoint() -> None:
            payload = {
                "complaint_id": "T-1",
                "description": "Cooling alarm fires repeatedly during use on device LX-200.",
            }
            kv("payload", payload)
            r = client.post("/triage", json=payload)
            assert r.status_code == 200, r.text
            body = r.json()
            kv("response", body)
            assert body["category"] == "hardware"

        results.append(run_step("POST /triage", case_endpoint))

    return print_summary(results)


if __name__ == "__main__":
    raise SystemExit(main())
