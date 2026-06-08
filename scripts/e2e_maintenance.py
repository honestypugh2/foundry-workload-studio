"""End-to-end smoke for the Preventative Maintenance Copilot."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from scripts.debug import (
    StepResult,
    kv,
    log_maintenance,
    log_telemetry_summary,
    print_summary,
    run_step,
    section,
)
from src.common.retrieval import LocalFolderRetriever
from src.maintenance_copilot.agent import recommend
from src.maintenance_copilot.api import create_app
from src.maintenance_copilot.telemetry_grounding import load_records, summarize

ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = ROOT / "data" / "telemetry" / "device_telemetry.json"
KB_DIR = ROOT / "data" / "clinical"


def main() -> int:
    results: list[StepResult] = []
    records = load_records(TELEMETRY_PATH)
    retriever = LocalFolderRetriever(KB_DIR)

    with section("Maintenance Copilot — telemetry summary"):

        def case_anomalous_device() -> None:
            summary = summarize(records, device_id="DEV-4421", window_hours=24)
            log_telemetry_summary(summary)
            assert summary.anomalies, "expected anomalies for DEV-4421"
            assert any("cooling_temp_c" in a for a in summary.anomalies)

        def case_clean_device() -> None:
            summary = summarize(records, device_id="DEV-4422", window_hours=24)
            log_telemetry_summary(summary)
            assert summary.anomalies == []

        def case_unknown_device() -> None:
            summary = summarize(records, device_id="DEV-9999", window_hours=24)
            log_telemetry_summary(summary)
            assert summary.anomalies == ["no_telemetry_for_device"]

        results.append(run_step("DEV-4421 anomalies detected", case_anomalous_device))
        results.append(run_step("DEV-4422 clean", case_clean_device))
        results.append(run_step("Unknown device flagged", case_unknown_device))

    with section("Maintenance Copilot — recommendation"):

        def case_recommend() -> None:
            summary = summarize(records, device_id="DEV-4421", window_hours=24)
            rec = recommend(summary, retriever=retriever)
            log_maintenance(rec)
            assert rec.recommended_actions
            assert rec.confidence > 0.0

        results.append(run_step("Recommendation grounded for DEV-4421", case_recommend))

    with section("Maintenance Copilot — FastAPI /recommend"):
        client = TestClient(create_app())

        def case_endpoint() -> None:
            payload = {"device_id": "DEV-4421", "window_hours": 24}
            kv("payload", payload)
            r = client.post("/recommend", json=payload)
            assert r.status_code == 200, r.text
            body = r.json()
            kv("response", body)
            assert body["device_id"] == "DEV-4421"
            assert body["recommended_actions"]

        results.append(run_step("POST /recommend", case_endpoint))

    return print_summary(results)


if __name__ == "__main__":
    raise SystemExit(main())
