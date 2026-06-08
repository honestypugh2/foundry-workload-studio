"""Tests for the Preventative Maintenance Copilot."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.common.retrieval import LocalFolderRetriever
from src.maintenance_copilot.agent import recommend
from src.maintenance_copilot.api import create_app
from src.maintenance_copilot.telemetry_grounding import load_records, summarize


def test_summary_flags_overheating_device(telemetry_path: Path) -> None:
    records = load_records(telemetry_path)
    summary = summarize(records, device_id="DEV-4421", window_hours=24)
    assert summary.metrics["cooling_temp_c_max"] >= 30
    assert summary.anomalies, "expected anomalies for DEV-4421"
    assert any("cooling_temp_c" in a for a in summary.anomalies)


def test_summary_clean_device_has_no_anomalies(telemetry_path: Path) -> None:
    records = load_records(telemetry_path)
    summary = summarize(records, device_id="DEV-4422", window_hours=24)
    assert summary.anomalies == []


def test_summary_unknown_device_signals_no_telemetry(telemetry_path: Path) -> None:
    records = load_records(telemetry_path)
    summary = summarize(records, device_id="DEV-9999", window_hours=24)
    assert summary.anomalies == ["no_telemetry_for_device"]


def test_recommend_combines_telemetry_and_kb(
    telemetry_path: Path, clinical_data_dir: Path
) -> None:
    records = load_records(telemetry_path)
    summary = summarize(records, device_id="DEV-4421", window_hours=24)
    rec = recommend(summary, retriever=LocalFolderRetriever(clinical_data_dir))
    assert rec.device_id == "DEV-4421"
    assert rec.recommended_actions
    assert rec.confidence > 0.0


def test_recommend_endpoint() -> None:
    client = TestClient(create_app())
    r = client.post("/recommend", json={"device_id": "DEV-4421", "window_hours": 24})
    assert r.status_code == 200
    body = r.json()
    assert body["device_id"] == "DEV-4421"
    assert body["recommended_actions"]
