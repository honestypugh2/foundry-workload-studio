"""Pytest configuration & fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests run in `test` environment with no Azure side effects."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ENABLE_TELEMETRY", "false")
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.services.ai.azure.com/api/projects/test")
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://example.search.windows.net")
    # Clear cached settings so each test sees fresh env.
    from src.common import config as cfg

    cfg.get_settings.cache_clear()
    yield
    cfg.get_settings.cache_clear()


@pytest.fixture
def hr_data_dir() -> Path:
    return ROOT / "data" / "hr"


@pytest.fixture
def clinical_data_dir() -> Path:
    return ROOT / "data" / "clinical"


@pytest.fixture
def complaints_path() -> Path:
    return ROOT / "data" / "complaints" / "sample_complaints.json"


@pytest.fixture
def telemetry_path() -> Path:
    return ROOT / "data" / "telemetry" / "device_telemetry.json"
