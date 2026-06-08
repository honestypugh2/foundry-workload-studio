"""Maintenance Copilot agent: combines telemetry summary with KB grounding."""

from __future__ import annotations

from pathlib import Path

from src.common.config import get_settings
from src.common.models import Citation, MaintenanceRecommendation, TelemetrySummary
from src.common.retrieval import AzureSearchRetriever, LocalFolderRetriever, Retriever

SYSTEM_PROMPT = (
    "You are a preventative maintenance copilot for medical device field "
    "engineers. Given a telemetry summary and grounded maintenance KB excerpts, "
    "recommend specific preventative actions ranked by urgency. Cite each "
    "recommendation. Never recommend bypassing safety interlocks."
)


def _default_retriever() -> Retriever:
    settings = get_settings()
    if settings.environment in {"dev", "test"} or "example" in settings.azure_search_endpoint:
        local = Path(__file__).resolve().parents[2] / "data" / "clinical"
        return LocalFolderRetriever(local)
    return AzureSearchRetriever(settings.azure_search_maintenance_index)


def _build_query(summary: TelemetrySummary) -> str:
    if summary.anomalies:
        return " ".join(summary.anomalies)
    return f"preventative maintenance {summary.device_id}"


def _confidence(summary: TelemetrySummary, citations: list[Citation]) -> float:
    if not citations:
        return 0.1
    base = 0.5 + min(0.4, 0.1 * len(citations))
    if summary.anomalies and summary.anomalies[0] != "no_telemetry_for_device":
        base += 0.1
    return round(min(base, 0.95), 2)


def _build_actions(summary: TelemetrySummary, citations: list[Citation]) -> list[str]:
    actions: list[str] = []
    for anomaly in summary.anomalies:
        if anomaly == "no_telemetry_for_device":
            actions.append("Verify device connectivity and telemetry pipeline.")
            continue
        actions.append(f"Inspect subsystem reporting: {anomaly}")
    if citations:
        top = citations[0]
        actions.append(f"Follow procedure in '{top.title}' for next scheduled service.")
    if not actions:
        actions.append("Continue scheduled preventative maintenance cadence.")
    return actions


def recommend(
    summary: TelemetrySummary,
    *,
    retriever: Retriever | None = None,
    model_call=None,
) -> MaintenanceRecommendation:
    retr = retriever or _default_retriever()
    query = _build_query(summary)
    citations = retr.retrieve(query, top=4)
    actions = _build_actions(summary, citations)
    reasoning = (
        f"Device {summary.device_id} window={summary.metric_window_hours}h. "
        f"Anomalies: {summary.anomalies or ['none']}."
    )

    call = model_call or _default_model_call()
    if call is not None:
        try:
            extra = call(SYSTEM_PROMPT, query, citations)
            if extra:
                reasoning = f"{reasoning}\n\nFoundry agent: {extra.strip()}"
        except Exception:  # noqa: S110 — never fail the demo on Foundry hiccups
            pass

    return MaintenanceRecommendation(
        device_id=summary.device_id,
        reasoning=reasoning,
        recommended_actions=actions,
        citations=citations,
        confidence=_confidence(summary, citations),
    )


def _default_model_call():
    """Return a Foundry-backed `ModelCall` when configured, else None."""
    from src.common.foundry_agents import is_foundry_configured, make_model_call

    if is_foundry_configured():
        return make_model_call("maintenance_copilot")
    return None
