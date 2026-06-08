"""Catalog of Azure services that back the platform.

Surfaced verbatim by the gateway at `/api/azure-services` so the frontend can
render an "Azure services in use" panel without hard-coding the list.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AzureServiceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str
    role: str
    docs_url: str


AZURE_SERVICES: list[AzureServiceInfo] = [
    AzureServiceInfo(
        id="foundry",
        name="Microsoft Foundry",
        category="AI Platform",
        role="Hosts the project, model deployments, and agent runtime.",
        docs_url="https://learn.microsoft.com/azure/ai-foundry/",
    ),
    AzureServiceInfo(
        id="ai-search",
        name="Azure AI Search",
        category="Knowledge",
        role="Hybrid + semantic retrieval index for grounded answers.",
        docs_url="https://learn.microsoft.com/azure/search/",
    ),
    AzureServiceInfo(
        id="cosmos-db",
        name="Azure Cosmos DB",
        category="Data",
        role="Conversation memory and triage history (NoSQL, low-latency).",
        docs_url="https://learn.microsoft.com/azure/cosmos-db/",
    ),
    AzureServiceInfo(
        id="storage",
        name="Azure Storage",
        category="Data",
        role="Source documents and ingestion staging (Blob, private).",
        docs_url="https://learn.microsoft.com/azure/storage/",
    ),
    AzureServiceInfo(
        id="key-vault",
        name="Azure Key Vault",
        category="Security",
        role="Stores credentials referenced by managed identity (RBAC).",
        docs_url="https://learn.microsoft.com/azure/key-vault/",
    ),
    AzureServiceInfo(
        id="container-apps",
        name="Azure Container Apps",
        category="Compute",
        role="Hosts the FastAPI services and gateway as serverless containers.",
        docs_url="https://learn.microsoft.com/azure/container-apps/",
    ),
    AzureServiceInfo(
        id="apim",
        name="Azure API Management",
        category="Networking",
        role="Front door for production traffic with throttling and policy.",
        docs_url="https://learn.microsoft.com/azure/api-management/",
    ),
    AzureServiceInfo(
        id="monitor",
        name="Azure Monitor + Application Insights",
        category="Observability",
        role="Telemetry, distributed tracing, and dashboards.",
        docs_url="https://learn.microsoft.com/azure/azure-monitor/",
    ),
]


class AzureServicesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    services: list[AzureServiceInfo] = Field(default_factory=list)
