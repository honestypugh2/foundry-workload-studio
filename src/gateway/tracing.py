"""Trace recorder that synthesises agent steps from inputs and responses.

Used by the gateway to give the frontend a deterministic timeline of what the
agent did without needing to instrument every internal call. When real
OpenTelemetry spans are available (Azure Monitor) the same model is populated
from them — the Pydantic shape stays identical.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class TraceStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: str = Field(default="ok", description="ok | warning | error")
    started_at: datetime
    duration_ms: float = Field(ge=0)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)


class TraceWorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    label: str | None = None


class TraceWorkflow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[str]
    edges: list[TraceWorkflowEdge]


class Trace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    use_case: str
    started_at: datetime
    duration_ms: float = Field(ge=0)
    steps: list[TraceStep] = Field(default_factory=list)
    azure_services_invoked: list[str] = Field(default_factory=list)
    workflow: TraceWorkflow | None = None


class TraceRecorder:
    """Lightweight in-process step recorder."""

    def __init__(self, use_case: str) -> None:
        self.run_id = uuid.uuid4().hex
        self.use_case = use_case
        self.started_at = datetime.now(UTC)
        self._t0 = time.perf_counter()
        self._steps: list[TraceStep] = []
        self._services: set[str] = set()

    @contextmanager
    def step(
        self,
        name: str,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> Iterator[dict[str, str | int | float | bool]]:
        started = datetime.now(UTC)
        t0 = time.perf_counter()
        attrs: dict[str, str | int | float | bool] = dict(attributes or {})
        status = "ok"
        try:
            yield attrs
        except Exception:
            status = "error"
            raise
        finally:
            self._steps.append(
                TraceStep(
                    name=name,
                    status=status,
                    started_at=started,
                    duration_ms=(time.perf_counter() - t0) * 1000.0,
                    attributes=attrs,
                )
            )

    def add_service(self, name: str) -> None:
        self._services.add(name)

    def build(self, workflow: TraceWorkflow | None = None) -> Trace:
        return Trace(
            run_id=self.run_id,
            use_case=self.use_case,
            started_at=self.started_at,
            duration_ms=(time.perf_counter() - self._t0) * 1000.0,
            steps=list(self._steps),
            azure_services_invoked=sorted(self._services),
            workflow=workflow,
        )
