"""Reusable grounded-answer composer.

Synthesizes an answer string from a question + retrieved citations. The actual
LLM call is delegated to a `model_call` callable so unit tests can substitute a
deterministic stub. In production, wire `model_call` to a Foundry agent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from src.common.models import ChatResponse, Citation
from src.common.safety import check_safety

ModelCall = Callable[[str, str, list[Citation]], str]
"""Signature: (system_prompt, user_question, citations) -> answer text."""

_NO_GROUND_MSG: Final = (
    "I don't have grounded information to answer that question. "
    "Please rephrase or contact your subject matter expert."
)


def compose_grounded_answer(
    *,
    system_prompt: str,
    question: str,
    citations: list[Citation],
    model_call: ModelCall,
    require_citations: bool = True,
    session_id: str | None = None,
) -> ChatResponse:
    """Run safety, retrieval guard, and assemble a `ChatResponse`."""
    verdict = check_safety(question)
    if not verdict.allowed:
        return ChatResponse(
            answer="Your question was blocked by content safety policy.",
            citations=[],
            session_id=session_id,
            grounded=False,
            escalation_recommended=True,
        )

    if require_citations and not citations:
        return ChatResponse(
            answer=_NO_GROUND_MSG,
            citations=[],
            session_id=session_id,
            grounded=False,
            escalation_recommended=True,
        )

    answer = model_call(system_prompt, question, citations)
    return ChatResponse(
        answer=answer,
        citations=citations,
        session_id=session_id,
        grounded=bool(citations),
    )
