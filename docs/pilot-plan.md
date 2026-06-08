# Pilot Plan

This accelerator is designed to move from POC → Pilot → Production in three phases.

## Phase 1 — POC (2 weeks)

**Goal:** Validate one grounded RAG use case (recommended: HR Policy Assistant).

- Provision `dev` environment with `infra/environments/dev.bicepparam`.
- Index sample HR markdown into Azure AI Search.
- Wire Foundry agent for grounded answers; demo to internal stakeholders.
- Capture eval metrics: groundedness, citation precision, latency.

## Phase 2 — Pilot (4–6 weeks)

**Goal:** Onboard a closed pilot group; introduce a second use case.

- Provision `demo` environment.
- Replace the offline `LocalFolderRetriever` with `AzureSearchRetriever`.
- Add Cosmos session persistence and Application Insights dashboards.
- Add the Quality Complaint Triage flow with structured output.
- Run shadow evaluations against historical complaints.

## Phase 3 — Production (8+ weeks)

**Goal:** Generally available with hardened security, scale, and governance.

- Provision `prod` environment (`infra/environments/prod.bicepparam`):
  - APIM front door for all use case APIs
  - Storage ZRS, Cosmos continuous backup
  - Key Vault purge protection enabled
  - Search service standard SKU with replicas=3, partitions=2
- RBAC-only data plane access via Managed Identity.
- Enforce content safety, eval gates in CI, and human-in-the-loop for safety-class outputs.
- Establish SLOs (p95 latency, groundedness) and incident runbooks.
