"""FastAPI app for the Preventative Maintenance Copilot."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from src.common.models import MaintenanceRecommendation
from src.common.telemetry import configure_telemetry
from src.maintenance_copilot.agent import recommend
from src.maintenance_copilot.telemetry_grounding import load_records, summarize

DEFAULT_TELEMETRY = Path(__file__).resolve().parents[2] / "data" / "telemetry" / "device_telemetry.json"


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1)
    window_hours: int = Field(default=24, ge=1, le=720)


def create_app() -> FastAPI:
    configure_telemetry()
    app = FastAPI(title="Preventative Maintenance Copilot", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/recommend", response_model=MaintenanceRecommendation)
    def recommend_route(req: RecommendRequest) -> MaintenanceRecommendation:
        records = load_records(DEFAULT_TELEMETRY) if DEFAULT_TELEMETRY.exists() else []
        summary = summarize(records, device_id=req.device_id, window_hours=req.window_hours)
        return recommend(summary)

    return app


app = create_app()
