"""FastAPI app for the Quality Complaint Triage workflow."""

from __future__ import annotations

from fastapi import FastAPI

from src.common.models import Complaint, ComplaintTriageResult
from src.common.telemetry import configure_telemetry
from src.quality_complaint_triage.agent import triage


def create_app() -> FastAPI:
    configure_telemetry()
    app = FastAPI(title="Quality Complaint Triage", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/triage", response_model=ComplaintTriageResult)
    def triage_route(complaint: Complaint) -> ComplaintTriageResult:
        return triage(complaint)

    return app


app = create_app()
