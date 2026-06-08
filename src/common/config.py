"""Centralized configuration with Pydantic Settings.

Loads from environment variables (and optional `.env` file). All secrets are
expected to come from environment / Azure Key Vault — never hard-coded.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "demo", "prod", "test"]


class Settings(BaseSettings):
    """Strongly-typed runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Foundry -----
    foundry_project_endpoint: str = Field(
        default="https://example.services.ai.azure.com/api/projects/test",
        description="Foundry project endpoint.",
    )
    foundry_model_deployment: str = Field(default="gpt-4o-mini")
    foundry_embedding_deployment: str = Field(default="text-embedding-3-small")

    # ----- Azure AI Search -----
    azure_search_endpoint: str = Field(default="https://example.search.windows.net")
    azure_search_api_key: str | None = None
    azure_search_hr_index: str = Field(default="hr-policies")
    azure_search_clinical_index: str = Field(default="clinical-laser")
    azure_search_maintenance_index: str = Field(default="maintenance-kb")

    # ----- Cosmos / Storage / KV -----
    azure_keyvault_uri: HttpUrl | None = None
    azure_cosmos_endpoint: HttpUrl | None = None
    azure_cosmos_database: str = Field(default="foundry-workload-studio")
    azure_storage_account: str | None = None
    azure_storage_container: str = Field(default="documents")

    # ----- Observability -----
    applicationinsights_connection_string: str | None = None
    enable_telemetry: bool = Field(default=True)

    # ----- Runtime -----
    environment: Environment = Field(default="dev")
    log_level: str = Field(default="INFO")

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
