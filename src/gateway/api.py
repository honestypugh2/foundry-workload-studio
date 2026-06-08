"""Unified FastAPI gateway for the React frontend."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from src.common.telemetry import configure_telemetry
from src.gateway.azure_services import AZURE_SERVICES, AzureServicesResponse
from src.gateway.registry import REGISTRY, UseCase, get_usecase, list_usecases
from src.gateway.status import StatusResponse, build_status
from src.gateway.tracing import Trace, TraceRecorder


class UseCaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    description: str
    category: str
    request_kind: str
    sample_input: dict[str, Any]
    azure_services: list[str]


class UseCaseDetail(UseCaseSummary):
    workflow: dict[str, Any]


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    use_case: str
    result: dict[str, Any]
    trace: Trace


def _summary(uc: UseCase) -> UseCaseSummary:
    return UseCaseSummary(
        slug=uc.slug,
        name=uc.name,
        description=uc.description,
        category=uc.category,
        request_kind=uc.request_kind,
        sample_input=uc.sample_input,
        azure_services=uc.azure_services,
    )


def create_app() -> FastAPI:
    configure_telemetry()
    app = FastAPI(title="Foundry Workload Studio — Gateway", version="0.1.0")

    # CORS for the Vite dev server (5173) and any deployed origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "use_cases": str(len(REGISTRY))}

    @app.get("/api/azure-services", response_model=AzureServicesResponse)
    def azure_services() -> AzureServicesResponse:
        return AzureServicesResponse(services=AZURE_SERVICES)

    @app.get("/api/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return build_status()

    @app.get("/api/usecases", response_model=list[UseCaseSummary])
    def usecases() -> list[UseCaseSummary]:
        return [_summary(uc) for uc in list_usecases()]

    @app.get("/api/usecases/{slug}", response_model=UseCaseDetail)
    def usecase_detail(slug: str) -> UseCaseDetail:
        uc = get_usecase(slug)
        if uc is None:
            raise HTTPException(status_code=404, detail=f"Unknown use case '{slug}'")
        return UseCaseDetail(**_summary(uc).model_dump(), workflow=uc.workflow.model_dump())

    @app.post("/api/usecases/{slug}/run", response_model=RunResponse)
    def run_usecase(slug: str, payload: dict[str, Any]) -> RunResponse:
        uc = get_usecase(slug)
        if uc is None:
            raise HTTPException(status_code=404, detail=f"Unknown use case '{slug}'")
        recorder = TraceRecorder(use_case=slug)
        with recorder.step("request_received", {"keys": ",".join(sorted(payload))}):
            pass
        try:
            result = uc.runner(payload, recorder)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with recorder.step("response_sent"):
            pass
        return RunResponse(
            use_case=slug,
            result=result.model_dump(mode="json"),
            trace=recorder.build(workflow=uc.workflow),
        )

    return app


app = create_app()
