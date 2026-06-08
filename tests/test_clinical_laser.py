"""Tests for the Clinical Laser Assistant."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.clinical_laser_assistant.agent import agent_answer
from src.clinical_laser_assistant.api import create_app
from src.common.retrieval import LocalFolderRetriever


def test_patient_specific_question_blocked(clinical_data_dir: Path) -> None:
    retr = LocalFolderRetriever(clinical_data_dir)
    resp = agent_answer("Should I treat this patient with the LX-200?", retriever=retr)
    assert resp.grounded is False
    assert resp.escalation_recommended is True
    assert resp.citations == []


def test_grounded_question_returns_citations(clinical_data_dir: Path) -> None:
    retr = LocalFolderRetriever(clinical_data_dir)
    resp = agent_answer(
        "What is the recommended cooling temperature range for the LX-200?",
        retriever=retr,
    )
    assert resp.grounded is True
    assert resp.citations
    assert any("laser" in c.source_id.lower() or "warning" in c.source_id.lower() for c in resp.citations)


def test_clinical_chat_endpoint() -> None:
    client = TestClient(create_app())
    r = client.post(
        "/chat",
        json={"question": "What should I do when the cooling alarm triggers?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert body["citations"]
