"""FastAPI app for the Clinical Laser Assistant."""

from __future__ import annotations

from fastapi import FastAPI

from src.clinical_laser_assistant.agent import agent_answer
from src.common.models import ChatRequest, ChatResponse
from src.common.telemetry import configure_telemetry


def create_app() -> FastAPI:
    configure_telemetry()
    app = FastAPI(title="Clinical Laser Assistant", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        return agent_answer(req.question, session_id=req.session_id)

    return app


app = create_app()
