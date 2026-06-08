"""Shared Pydantic models used across use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Citation(BaseModel):
    """A grounded citation referencing a source document/chunk."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    url: str | None = None
    snippet: str = Field(max_length=1500)
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class ChatRequest(BaseModel):
    """Chat request body for any RAG-style assistant."""

    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, Field(min_length=1, max_length=4000)]
    session_id: str | None = None
    user_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response containing the answer and grounded citations."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    session_id: str | None = None
    grounded: bool = True
    escalation_recommended: bool = False
    created_at: datetime = Field(default_factory=_utcnow)


# ----- Quality Complaint Triage -----


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplaintCategory(StrEnum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    USAGE = "usage"
    SAFETY = "safety"
    OTHER = "other"


class Complaint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_id: str
    customer_id: str | None = None
    device_model: str | None = None
    description: Annotated[str, Field(min_length=5, max_length=8000)]
    submitted_at: datetime = Field(default_factory=_utcnow)


class ComplaintTriageResult(BaseModel):
    """Structured output returned by the triage agent."""

    model_config = ConfigDict(extra="forbid")

    complaint_id: str
    category: ComplaintCategory
    severity: Severity
    summary: Annotated[str, Field(max_length=500)]
    suggested_route: str = Field(description="Team/queue to route the issue to.")
    requires_escalation: bool = False
    extracted_entities: dict[str, str] = Field(default_factory=dict)
    triaged_at: datetime = Field(default_factory=_utcnow)


# ----- Preventative Maintenance -----


class TelemetryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str
    timestamp: datetime
    metric: str
    value: float
    unit: str | None = None


class TelemetrySummary(BaseModel):
    """Lightweight summary of recent telemetry for a device."""

    model_config = ConfigDict(extra="forbid")

    device_id: str
    metric_window_hours: int = Field(ge=1, le=720)
    metrics: dict[str, float] = Field(
        description="Aggregated metrics (e.g. {'cooling_temp_avg': 72.4})."
    )
    anomalies: list[str] = Field(default_factory=list)

    @field_validator("metrics")
    @classmethod
    def _no_empty_metrics(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("metrics must contain at least one entry")
        return v


class MaintenanceRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str
    reasoning: str
    recommended_actions: list[str]
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
