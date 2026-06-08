"""Foundry client factory.

Centralizes credentials (DefaultAzureCredential), Foundry project endpoint,
and AI Search clients so each use case stays thin.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from src.common.config import Settings, get_settings

if TYPE_CHECKING:
    from azure.ai.projects import AIProjectClient
    from azure.search.documents import SearchClient


@lru_cache(maxsize=1)
def get_credential() -> TokenCredential:
    """Return a cached DefaultAzureCredential instance."""
    return DefaultAzureCredential()


def build_project_client(settings: Settings | None = None) -> AIProjectClient:
    """Build a Foundry `AIProjectClient` bound to the configured project."""
    from azure.ai.projects import AIProjectClient  # local import to keep import cost low

    cfg = settings or get_settings()
    return AIProjectClient(
        endpoint=cfg.foundry_project_endpoint,
        credential=get_credential(),
    )


def build_search_client(index_name: str, settings: Settings | None = None) -> SearchClient:
    """Build an Azure AI Search client for the given index."""
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    cfg = settings or get_settings()
    credential: TokenCredential | AzureKeyCredential = (
        AzureKeyCredential(cfg.azure_search_api_key)
        if cfg.azure_search_api_key
        else get_credential()
    )
    return SearchClient(
        endpoint=cfg.azure_search_endpoint,
        index_name=index_name,
        credential=credential,
    )
