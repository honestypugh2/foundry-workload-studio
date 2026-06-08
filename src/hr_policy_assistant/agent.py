"""HR Policy Assistant agent.

Implements the `agent_answer` entry point used by the FastAPI route. By default
it uses the `LocalFolderRetriever` so the assistant works offline; in production
it should be wired to `AzureSearchRetriever` against the `hr-policies` index.
"""

from __future__ import annotations

from pathlib import Path

from src.common.config import get_settings
from src.common.grounded import compose_grounded_answer
from src.common.models import ChatResponse, Citation
from src.common.retrieval import AzureSearchRetriever, LocalFolderRetriever, Retriever

SYSTEM_PROMPT = (
    "You are the HR Policy Assistant for an enterprise organization. "
    "Answer employee questions about benefits, PTO, leave, and the employee "
    "handbook using ONLY the provided policy excerpts. Always cite the policy "
    "title. If the policy does not address the question, say so and route the "
    "user to HR Business Partners. Never disclose personal employee data."
)


def _default_retriever() -> Retriever:
    settings = get_settings()
    if settings.environment in {"dev", "test"} or "example" in settings.azure_search_endpoint:
        local = Path(__file__).resolve().parents[2] / "data" / "hr"
        return LocalFolderRetriever(local)
    return AzureSearchRetriever(settings.azure_search_hr_index)


def _stub_model_call(_system: str, question: str, citations: list[Citation]) -> str:
    """Deterministic answer composer used when no live Foundry call is wired."""
    top = citations[0]
    return (
        f"Based on **{top.title}**: {top.snippet[:600].strip()}\n\n"
        f"(Question: {question})"
    )


def agent_answer(
    question: str,
    *,
    session_id: str | None = None,
    retriever: Retriever | None = None,
    model_call=None,
) -> ChatResponse:
    """Answer an HR policy question with citations."""
    retr = retriever or _default_retriever()
    citations = retr.retrieve(question, top=4)
    return compose_grounded_answer(
        system_prompt=SYSTEM_PROMPT,
        question=question,
        citations=citations,
        model_call=model_call or _default_model_call(),
        session_id=session_id,
        require_citations=True,
    )


def _default_model_call():
    """Use the Foundry persistent agent when configured; otherwise stub."""
    from src.common.foundry_agents import is_foundry_configured, make_model_call

    if is_foundry_configured():
        return make_model_call("hr_policy_assistant")
    return _stub_model_call
