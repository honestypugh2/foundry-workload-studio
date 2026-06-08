"""Clinical Laser Assistant agent — strict citation + safety enforcement."""

from __future__ import annotations

from pathlib import Path

from src.common.config import get_settings
from src.common.grounded import compose_grounded_answer
from src.common.models import ChatResponse, Citation
from src.common.retrieval import AzureSearchRetriever, LocalFolderRetriever, Retriever

SYSTEM_PROMPT = (
    "You are a Clinical Laser Product Assistant for trained clinicians. "
    "Provide grounded answers about laser device operation, maintenance, "
    "warnings, and contraindications using ONLY the supplied product "
    "documentation. Always include the source document title. Never provide "
    "patient-specific medical advice. If the question concerns patient "
    "diagnosis or treatment selection, decline and recommend contacting the "
    "treating physician. If documentation does not cover the question, say so."
)


def _default_retriever() -> Retriever:
    settings = get_settings()
    if settings.environment in {"dev", "test"} or "example" in settings.azure_search_endpoint:
        local = Path(__file__).resolve().parents[2] / "data" / "clinical"
        return LocalFolderRetriever(local)
    return AzureSearchRetriever(settings.azure_search_clinical_index)


_PATIENT_TRIGGERS = (
    "my patient",
    "should i treat",
    "diagnose",
    "treat this patient",
)


def _stub_model_call(_system: str, question: str, citations: list[Citation]) -> str:
    top = citations[0]
    return (
        f"According to **{top.title}**:\n\n{top.snippet[:800].strip()}\n\n"
        f"Always follow institutional protocols and consult the device IFU."
    )


def agent_answer(
    question: str,
    *,
    session_id: str | None = None,
    retriever: Retriever | None = None,
    model_call=None,
) -> ChatResponse:
    lowered = question.lower()
    if any(trigger in lowered for trigger in _PATIENT_TRIGGERS):
        return ChatResponse(
            answer=(
                "I can't provide patient-specific clinical advice. Please consult "
                "the treating physician and the device Instructions for Use (IFU)."
            ),
            citations=[],
            session_id=session_id,
            grounded=False,
            escalation_recommended=True,
        )

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
        return make_model_call("clinical_laser_assistant")
    return _stub_model_call
