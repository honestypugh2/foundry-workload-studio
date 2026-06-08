"""Runtime mode + Azure connectivity status surfaced at `/api/status`.

The frontend uses this to display a clear banner showing whether the app is
running in offline `dev`/`test` mode or actually connected to Azure (`demo`,
`prod`).
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.common.config import Settings, get_settings
from src.common.foundry_agents import is_foundry_configured

log = logging.getLogger(__name__)

ServiceState = Literal["live", "configured", "unconfigured", "error"]


class ServiceStatus(BaseModel):
    """Status of a single Azure service binding."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: ServiceState
    endpoint: str | None = None
    detail: str | None = None


class StatusResponse(BaseModel):
    """Top-level runtime status returned from `/api/status`."""

    model_config = ConfigDict(extra="forbid")

    environment: str
    mode: Literal["offline", "live"]
    foundry_model_deployment: str
    services: list[ServiceStatus] = Field(default_factory=list)


def _has_real(value: str | None) -> bool:
    return bool(value) and "example" not in (value or "").lower()


def _probe_foundry(cfg: Settings) -> ServiceStatus:
    if not is_foundry_configured(cfg):
        return ServiceStatus(
            id="foundry",
            state="unconfigured",
            endpoint=cfg.foundry_project_endpoint,
            detail="Offline stub mode (ENVIRONMENT=dev or example endpoint).",
        )
    try:
        from src.common.foundry_agents import _project_client

        client = _project_client(cfg)
        names = [a.name for a in client.agents.list(limit=10)]
        return ServiceStatus(
            id="foundry",
            state="live",
            endpoint=cfg.foundry_project_endpoint,
            detail=(
                f"Connected. {len(names)} agent(s): {', '.join(names) or 'none'}"
            ),
        )
    except Exception as exc:
        log.warning("Foundry probe failed: %s", exc)
        return ServiceStatus(
            id="foundry",
            state="error",
            endpoint=cfg.foundry_project_endpoint,
            detail=f"{type(exc).__name__}: {exc}"[:200],
        )


def _probe_search(cfg: Settings) -> ServiceStatus:
    if not _has_real(cfg.azure_search_endpoint):
        return ServiceStatus(
            id="ai-search",
            state="unconfigured",
            endpoint=cfg.azure_search_endpoint,
            detail="Using local folder retriever.",
        )
    return ServiceStatus(
        id="ai-search",
        state="configured",
        endpoint=cfg.azure_search_endpoint,
        detail=(
            f"Indexes: {cfg.azure_search_hr_index}, "
            f"{cfg.azure_search_clinical_index}, "
            f"{cfg.azure_search_maintenance_index}"
        ),
    )


def _probe_storage(cfg: Settings) -> ServiceStatus:
    if not cfg.azure_storage_account:
        return ServiceStatus(
            id="storage",
            state="unconfigured",
            detail="Using local data/telemetry/*.json.",
        )
    return ServiceStatus(
        id="storage",
        state="configured",
        endpoint=f"https://{cfg.azure_storage_account}.blob.core.windows.net/",
        detail=f"Container: {cfg.azure_storage_container}",
    )


def _probe_keyvault(cfg: Settings) -> ServiceStatus:
    if cfg.azure_keyvault_uri is None:
        return ServiceStatus(id="key-vault", state="unconfigured")
    return ServiceStatus(
        id="key-vault",
        state="configured",
        endpoint=str(cfg.azure_keyvault_uri),
    )


def _probe_cosmos(cfg: Settings) -> ServiceStatus:
    if cfg.azure_cosmos_endpoint is None:
        return ServiceStatus(
            id="cosmos-db",
            state="unconfigured",
            detail="Cosmos not deployed in this environment.",
        )
    return ServiceStatus(
        id="cosmos-db",
        state="configured",
        endpoint=str(cfg.azure_cosmos_endpoint),
        detail=f"Database: {cfg.azure_cosmos_database}",
    )


def _probe_monitor(cfg: Settings) -> ServiceStatus:
    if not cfg.applicationinsights_connection_string:
        return ServiceStatus(id="monitor", state="unconfigured")
    return ServiceStatus(
        id="monitor",
        state="configured",
        detail="Application Insights connection string configured.",
    )


def build_status(settings: Settings | None = None) -> StatusResponse:
    """Probe configured Azure services and return a `StatusResponse`."""
    cfg = settings or get_settings()
    services = [
        _probe_foundry(cfg),
        _probe_search(cfg),
        _probe_storage(cfg),
        _probe_keyvault(cfg),
        _probe_cosmos(cfg),
        _probe_monitor(cfg),
    ]
    any_live = any(s.state == "live" for s in services)
    any_configured = any(s.state in {"live", "configured"} for s in services)
    mode: Literal["offline", "live"] = (
        "live" if (any_live or (cfg.environment != "dev" and any_configured)) else "offline"
    )
    return StatusResponse(
        environment=cfg.environment,
        mode=mode,
        foundry_model_deployment=cfg.foundry_model_deployment,
        services=services,
    )
