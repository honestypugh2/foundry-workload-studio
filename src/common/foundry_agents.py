"""Foundry persistent-agent helpers (v2 Agents API).

Provides idempotent provisioning + invocation of Foundry **prompt agents**
using the `azure-ai-projects` v2 SDK. Agents created via this module appear
in ai.azure.com → Project → **Agents**.

Design goals
------------
* **Idempotent**: `ensure_agent("clinical_laser_assistant")` looks up by
  agent name first; only creates a new version if missing or definition drifted.
* **Lazy**: Azure SDK is imported only when actually invoking Foundry, so
  unit tests stay offline.
* **Injectable**: each use-case agent module gets a `model_call` factory
  matching `compose_grounded_answer`'s `ModelCall` signature, but tests can
  still pass their own stub.

A single source of truth for the spec list lives in `AGENT_SPECS`.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.common.config import Settings, get_settings
from src.common.models import Citation

if TYPE_CHECKING:
    from azure.ai.projects import AIProjectClient

log = logging.getLogger(__name__)

ModelCall = Callable[[str, str, list[Citation]], str]
"""Matches `src.common.grounded.ModelCall`."""


# ---------------------------------------------------------------------------
# Specs — source of truth for what shows up in the Foundry portal.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentSpec:
    """Declarative spec for a Foundry prompt agent."""

    key: str  # internal stable key (matches Python module name)
    name: str  # display name shown in the Foundry portal (must be DNS-safe)
    description: str
    instructions: str
    response_format: str | None = None  # e.g. "json_object" for structured output


# Imports at module level keep the system prompts identical between the local
# stub path and the Foundry path.
from src.clinical_laser_assistant.agent import SYSTEM_PROMPT as CLINICAL_PROMPT  # noqa: E402
from src.hr_policy_assistant.agent import SYSTEM_PROMPT as HR_PROMPT  # noqa: E402
from src.maintenance_copilot.agent import SYSTEM_PROMPT as MAINT_PROMPT  # noqa: E402
from src.quality_complaint_triage.agent import SYSTEM_PROMPT as TRIAGE_PROMPT  # noqa: E402

AGENT_SPECS: dict[str, AgentSpec] = {
    "clinical_laser_assistant": AgentSpec(
        key="clinical_laser_assistant",
        name="clinical-laser-assistant",
        description="Grounded Q&A for clinicians on laser device IFU/maintenance.",
        instructions=CLINICAL_PROMPT,
    ),
    "hr_policy_assistant": AgentSpec(
        key="hr_policy_assistant",
        name="hr-policy-assistant",
        description="Grounded Q&A over HR benefits/PTO/handbook policies.",
        instructions=HR_PROMPT,
    ),
    "maintenance_copilot": AgentSpec(
        key="maintenance_copilot",
        name="maintenance-copilot",
        description="Preventative-maintenance recommendations from telemetry + KB.",
        instructions=MAINT_PROMPT,
    ),
    "quality_complaint_triage": AgentSpec(
        key="quality_complaint_triage",
        name="quality-complaint-triage",
        description="Classifies device complaints into category/severity JSON.",
        instructions=TRIAGE_PROMPT,
        response_format="json_object",
    ),
}


# ---------------------------------------------------------------------------
# Activation gate — keep tests/dev fully offline.
# ---------------------------------------------------------------------------


def is_foundry_configured(settings: Settings | None = None) -> bool:
    """True only when a real Foundry project endpoint is configured."""
    cfg = settings or get_settings()
    if cfg.environment in {"dev", "test"}:
        return False
    return "example" not in cfg.foundry_project_endpoint


# ---------------------------------------------------------------------------
# Idempotent provisioning (v2 Agents API).
# ---------------------------------------------------------------------------


_agent_name_cache: dict[str, str] = {}
_cache_lock = threading.Lock()


def _project_client(settings: Settings | None = None) -> AIProjectClient:
    """Build an `AIProjectClient` against the configured Foundry project.

    `allow_preview=True` is required to scope the embedded OpenAI client at an
    agent endpoint via `get_openai_client(agent_name=...)`.
    """
    from azure.ai.projects import AIProjectClient

    from src.common.foundry_client import get_credential

    cfg = settings or get_settings()
    return AIProjectClient(
        endpoint=cfg.foundry_project_endpoint,
        credential=get_credential(),
        allow_preview=True,
    )


def _build_definition(spec: AgentSpec, cfg: Settings) -> Any:
    """Build a `PromptAgentDefinition` for the spec."""
    from azure.ai.projects.models import (
        PromptAgentDefinition,
        PromptAgentDefinitionTextOptions,
        TextResponseFormatJsonObject,
    )

    text: PromptAgentDefinitionTextOptions | None = None
    if spec.response_format == "json_object":
        text = PromptAgentDefinitionTextOptions(format=TextResponseFormatJsonObject())

    return PromptAgentDefinition(
        model=cfg.foundry_model_deployment,
        instructions=spec.instructions,
        text=text,
    )


def _definitions_match(existing: Any, desired: Any) -> bool:
    """Best-effort drift detection by comparing instructions + model."""
    try:
        return (
            getattr(existing, "instructions", None) == getattr(desired, "instructions", None)
            and getattr(existing, "model", None) == getattr(desired, "model", None)
        )
    except Exception:
        return False


def ensure_agent(key: str, *, settings: Settings | None = None) -> str:
    """Return the Foundry agent **name** for `key`, creating it if missing.

    With the v2 API agents are addressed by name (not GUID id). If an agent
    with `spec.name` already exists, this returns its name; if its latest
    version's definition drifted, a new version is created.
    """
    with _cache_lock:
        if key in _agent_name_cache:
            return _agent_name_cache[key]

    spec = AGENT_SPECS[key]
    cfg = settings or get_settings()
    client = _project_client(cfg)

    desired = _build_definition(spec, cfg)

    # Look up existing agent's latest version.
    existing_latest: Any | None = None
    try:
        for v in client.agents.list_versions(spec.name, limit=1, order="desc"):
            existing_latest = v
            break
    except Exception:
        existing_latest = None

    if existing_latest is None:
        log.info("Creating Foundry agent %s (model=%s)", spec.name, cfg.foundry_model_deployment)
        client.agents.create_version(
            spec.name,
            definition=desired,
            description=spec.description,
        )
    elif not _definitions_match(existing_latest.definition, desired):
        log.info("Definition drift detected for %s — creating new version", spec.name)
        client.agents.create_version(
            spec.name,
            definition=desired,
            description=spec.description,
        )
    else:
        log.info("Foundry agent %s already up-to-date", spec.name)

    with _cache_lock:
        _agent_name_cache[key] = spec.name
    return spec.name


def provision_all(settings: Settings | None = None) -> dict[str, str]:
    """Ensure every agent in `AGENT_SPECS` exists. Returns {key: agent_name}."""
    return {key: ensure_agent(key, settings=settings) for key in AGENT_SPECS}


def delete_agent(name: str, *, settings: Settings | None = None) -> None:
    """Force-delete an agent by name."""
    cfg = settings or get_settings()
    client = _project_client(cfg)
    try:
        client.agents.delete(name, force=True)
        log.info("Deleted Foundry agent %s", name)
    except Exception as exc:
        log.warning("Failed to delete agent %s: %s", name, exc)


# ---------------------------------------------------------------------------
# Invocation via the OpenAI Responses API scoped to the agent endpoint.
# ---------------------------------------------------------------------------


def _format_citations(citations: list[Citation]) -> str:
    if not citations:
        return ""
    lines = ["", "---", "Use ONLY the following grounded citations:"]
    for i, c in enumerate(citations, 1):
        lines.append(f"[{i}] {c.title} (source_id={c.source_id})")
        lines.append(c.snippet[:1200])
    return "\n".join(lines)


def run_agent(
    key: str,
    user_message: str,
    *,
    citations: list[Citation] | None = None,
    settings: Settings | None = None,
) -> str:
    """Run the named agent on a single user message and return its text reply.

    Uses the OpenAI **Responses API** scoped to the agent's endpoint via
    `AIProjectClient.get_openai_client(agent_name=...)`.
    """
    cfg = settings or get_settings()
    name = ensure_agent(key, settings=cfg)
    client = _project_client(cfg)

    oai = client.get_openai_client(agent_name=name)
    content = user_message + _format_citations(citations or [])
    resp = oai.responses.create(model=cfg.foundry_model_deployment, input=content)

    text = getattr(resp, "output_text", None)
    if text:
        return text
    # Fallback: walk the structured output.
    parts: list[str] = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            t = getattr(c, "text", None)
            if isinstance(t, str):
                parts.append(t)
    return "".join(parts)


def make_model_call(key: str, *, settings: Settings | None = None) -> ModelCall:
    """Return a `ModelCall` that delegates to the named Foundry agent."""

    def _call(_system: str, question: str, citations: list[Citation]) -> str:
        return run_agent(key, question, citations=citations, settings=settings)

    return _call
