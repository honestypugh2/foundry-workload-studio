"""Use-case registry consumed by the gateway and the React frontend.

Adding a new use case is intentionally cheap: implement an agent function,
write a `UseCase` entry below, and the UI picks it up automatically via
`/api/usecases`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.clinical_laser_assistant.agent import agent_answer as clinical_answer
from src.common.config import get_settings
from src.common.models import (
    ChatRequest,
    ChatResponse,
    Complaint,
    ComplaintTriageResult,
    MaintenanceRecommendation,
)
from src.gateway.tracing import TraceRecorder, TraceWorkflow, TraceWorkflowEdge
from src.hr_policy_assistant.agent import agent_answer as hr_answer
from src.maintenance_copilot.agent import recommend as maintenance_recommend
from src.maintenance_copilot.telemetry_grounding import (
    load_records,
    load_records_from_blob,
    summarize,
)
from src.quality_complaint_triage.agent import triage as triage_complaint

# ----- Schemas -----------------------------------------------------------------


class MaintenanceRunRequest(BaseModel):
    """Request body for the maintenance copilot."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1)
    window_hours: int = Field(default=24, ge=1, le=720)


# ----- Workflows ---------------------------------------------------------------


def _rag_workflow() -> TraceWorkflow:
    return TraceWorkflow(
        nodes=["request", "safety_pre_check", "retrieve", "compose_answer", "response"],
        edges=[
            TraceWorkflowEdge(source="request", target="safety_pre_check"),
            TraceWorkflowEdge(source="safety_pre_check", target="retrieve", label="allow"),
            TraceWorkflowEdge(source="safety_pre_check", target="response", label="block"),
            TraceWorkflowEdge(source="retrieve", target="compose_answer"),
            TraceWorkflowEdge(source="compose_answer", target="response"),
        ],
    )


def _triage_workflow() -> TraceWorkflow:
    return TraceWorkflow(
        nodes=["complaint", "classify", "extract_entities", "route", "response"],
        edges=[
            TraceWorkflowEdge(source="complaint", target="classify"),
            TraceWorkflowEdge(source="classify", target="extract_entities"),
            TraceWorkflowEdge(source="extract_entities", target="route"),
            TraceWorkflowEdge(source="route", target="response"),
        ],
    )


def _maintenance_workflow() -> TraceWorkflow:
    return TraceWorkflow(
        nodes=["request", "load_telemetry", "summarize", "ground_recommendation", "response"],
        edges=[
            TraceWorkflowEdge(source="request", target="load_telemetry"),
            TraceWorkflowEdge(source="load_telemetry", target="summarize"),
            TraceWorkflowEdge(source="summarize", target="ground_recommendation"),
            TraceWorkflowEdge(source="ground_recommendation", target="response"),
        ],
    )


# ----- Runners -----------------------------------------------------------------

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
TELEMETRY_PATH = DATA_ROOT / "telemetry" / "device_telemetry.json"


def _run_rag(
    runner: Callable[..., ChatResponse], req: ChatRequest, recorder: TraceRecorder
) -> ChatResponse:
    recorder.add_service("foundry")
    recorder.add_service("ai-search")
    recorder.add_service("monitor")
    with recorder.step(
        "safety_pre_check", {"question_chars": len(req.question)}
    ):
        pass
    with recorder.step("retrieve", {"top_k": 4}) as attrs:
        response = runner(req.question, session_id=req.session_id)
        attrs["citations"] = len(response.citations)
        attrs["grounded"] = response.grounded
    with recorder.step(
        "compose_answer",
        {"escalation_recommended": response.escalation_recommended},
    ):
        pass
    return response


def _run_hr(payload: dict[str, Any], recorder: TraceRecorder) -> ChatResponse:
    return _run_rag(hr_answer, ChatRequest.model_validate(payload), recorder)


def _run_clinical(payload: dict[str, Any], recorder: TraceRecorder) -> ChatResponse:
    return _run_rag(clinical_answer, ChatRequest.model_validate(payload), recorder)


def _run_complaint(payload: dict[str, Any], recorder: TraceRecorder) -> ComplaintTriageResult:
    recorder.add_service("foundry")
    recorder.add_service("monitor")
    complaint = Complaint.model_validate(payload)
    with recorder.step(
        "classify", {"complaint_id": complaint.complaint_id}
    ) as attrs:
        result = triage_complaint(complaint)
        attrs["category"] = result.category.value
        attrs["severity"] = result.severity.value
    with recorder.step(
        "extract_entities", {"entities": len(result.extracted_entities)}
    ):
        pass
    with recorder.step(
        "route",
        {
            "queue": result.suggested_route,
            "requires_escalation": result.requires_escalation,
        },
    ):
        pass
    return result


def _run_maintenance(
    payload: dict[str, Any], recorder: TraceRecorder
) -> MaintenanceRecommendation:
    recorder.add_service("foundry")
    recorder.add_service("ai-search")
    recorder.add_service("storage")
    recorder.add_service("monitor")
    req = MaintenanceRunRequest.model_validate(payload)
    settings = get_settings()
    use_blob = bool(settings.azure_storage_account) and settings.environment != "test"
    with recorder.step(
        "load_telemetry",
        {
            "source": "blob" if use_blob else "local",
            "path": "telemetry/device_telemetry.json"
            if use_blob
            else str(TELEMETRY_PATH.name),
        },
    ) as attrs:
        if use_blob:
            try:
                records = load_records_from_blob(account=settings.azure_storage_account)
                attrs["account"] = settings.azure_storage_account
            except Exception as exc:  # pragma: no cover - blob fallback
                attrs["blob_error"] = type(exc).__name__
                records = load_records(TELEMETRY_PATH) if TELEMETRY_PATH.exists() else []
                attrs["source"] = "local-fallback"
        else:
            records = load_records(TELEMETRY_PATH) if TELEMETRY_PATH.exists() else []
        attrs["records"] = len(records)
    with recorder.step(
        "summarize",
        {"device_id": req.device_id, "window_hours": req.window_hours},
    ) as attrs:
        summary = summarize(
            records, device_id=req.device_id, window_hours=req.window_hours
        )
        attrs["anomalies"] = len(summary.anomalies)
    with recorder.step(
        "ground_recommendation", {"metrics": len(summary.metrics)}
    ) as attrs:
        result = recommend(summary)
        attrs["citations"] = len(result.citations)
        attrs["confidence"] = result.confidence
    return result


def recommend(summary: Any) -> MaintenanceRecommendation:  # pragma: no cover - thin shim
    return maintenance_recommend(summary)


# ----- Registry ---------------------------------------------------------------


class UseCase(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    slug: str
    name: str
    description: str
    category: str
    request_kind: str = Field(description="Hint to the UI: 'chat' | 'complaint' | 'maintenance'")
    sample_input: dict[str, Any]
    azure_services: list[str]
    workflow: TraceWorkflow
    runner: Callable[[dict[str, Any], TraceRecorder], BaseModel] = Field(exclude=True)


REGISTRY: dict[str, UseCase] = {
    "hr-policy-assistant": UseCase(
        slug="hr-policy-assistant",
        name="HR Policy Assistant",
        description="Answers HR / benefits questions grounded in company policy documents.",
        category="Knowledge / RAG",
        request_kind="chat",
        sample_input={"question": "How many vacation days do new hires accrue?"},
        azure_services=["foundry", "ai-search", "monitor"],
        workflow=_rag_workflow(),
        runner=_run_hr,
    ),
    "clinical-laser-assistant": UseCase(
        slug="clinical-laser-assistant",
        name="Clinical Laser Assistant",
        description="Grounded answers about laser device operation, warnings, and IFU.",
        category="Knowledge / RAG",
        request_kind="chat",
        sample_input={
            "question": "What are the contraindications listed in the IFU?"
        },
        azure_services=["foundry", "ai-search", "monitor"],
        workflow=_rag_workflow(),
        runner=_run_clinical,
    ),
    "quality-complaint-triage": UseCase(
        slug="quality-complaint-triage",
        name="Quality Complaint Triage",
        description="Classifies device complaints, extracts entities, and routes them.",
        category="Structured Output",
        request_kind="complaint",
        sample_input={
            "complaint_id": "C-1042",
            "customer_id": "CU-7781",
            "device_model": "DEV-22",
            "description": (
                "DEV-22 unit shut down mid-procedure with E-105 cooling fault."
            ),
        },
        azure_services=["foundry", "monitor"],
        workflow=_triage_workflow(),
        runner=_run_complaint,
    ),
    "maintenance-copilot": UseCase(
        slug="maintenance-copilot",
        name="Preventative Maintenance Copilot",
        description=(
            "Summarises device telemetry and produces grounded maintenance "
            "recommendations."
        ),
        category="Telemetry + RAG",
        request_kind="maintenance",
        sample_input={"device_id": "DEV-4421", "window_hours": 24},
        azure_services=["foundry", "ai-search", "storage", "monitor"],
        workflow=_maintenance_workflow(),
        runner=_run_maintenance,
    ),
}


def list_usecases() -> list[UseCase]:
    return list(REGISTRY.values())


def get_usecase(slug: str) -> UseCase | None:
    return REGISTRY.get(slug)
