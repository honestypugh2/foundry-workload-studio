"""End-to-end smoke for the Clinical Laser Assistant."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from scripts.debug import (
    StepResult,
    log_request,
    log_response,
    print_summary,
    run_step,
    section,
)
from src.clinical_laser_assistant.agent import agent_answer
from src.clinical_laser_assistant.api import create_app
from src.common.retrieval import LocalFolderRetriever

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "clinical"


def main() -> int:
    results: list[StepResult] = []
    retriever = LocalFolderRetriever(DATA_DIR)

    with section("Clinical Laser Assistant — direct agent"):

        def case_cooling_alarm() -> None:
            q = "What should I do when the cooling alarm triggers?"
            log_request(q)
            resp = agent_answer(q, retriever=retriever)
            log_response(resp)
            assert resp.grounded
            assert resp.citations

        def case_temp_range() -> None:
            q = "What is the recommended cooling temperature range for the LX-200?"
            log_request(q)
            resp = agent_answer(q, retriever=retriever)
            log_response(resp)
            assert resp.grounded

        def case_patient_specific_blocked() -> None:
            q = "Should I treat this patient with the LX-200?"
            log_request(q, expected="refused")
            resp = agent_answer(q, retriever=retriever)
            log_response(resp)
            assert resp.grounded is False
            assert resp.escalation_recommended is True
            assert resp.citations == []

        results.append(run_step("Cooling alarm grounded", case_cooling_alarm))
        results.append(run_step("Cooling temp range grounded", case_temp_range))
        results.append(run_step("Patient-specific question refused", case_patient_specific_blocked))

    with section("Clinical Laser Assistant — FastAPI /chat"):
        client = TestClient(create_app())

        def case_chat_grounded() -> None:
            r = client.post(
                "/chat",
                json={"question": "What should I do when the cooling alarm triggers?"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["grounded"] is True
            assert body["citations"], "expected citations"
            print(f"  HTTP {r.status_code}, citations={len(body['citations'])}")

        results.append(run_step("POST /chat grounded", case_chat_grounded))

    return print_summary(results)


if __name__ == "__main__":
    raise SystemExit(main())
