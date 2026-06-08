# Security & Responsible AI Guardrails

## Identity & Access

- All Azure resources use **Managed Identity**. `disableLocalAuth=true` on Search, Cognitive Services, and Storage shared-key access disabled.
- Key Vault is **RBAC-only**. Production enables purge protection.
- Principal-level role assignments are parameterized via `principalId` in `main.bicep`.

## Data Protection

- Storage: TLS 1.2 minimum, no public blob access, ZRS in production.
- Cosmos: Continuous backup in production, periodic backups otherwise.
- All secrets sourced from environment / Key Vault — no secrets in code or in `.env.example` defaults.

## Responsible AI

- **Grounded-only answers**: `compose_grounded_answer` returns a refusal when no citations are retrieved (`grounded=False`, `escalation_recommended=True`).
- **Citation enforcement**: Every grounded response includes the source title and snippet.
- **Clinical guardrails**: Patient-specific questions are refused and routed to the treating physician.
- **Prompt-injection filter**: `check_safety` blocks common jailbreak patterns and PHI hints prior to model invocation.
- **Structured output**: Triage agent returns a Pydantic-validated `ComplaintTriageResult` to avoid free-form hallucination on routing decisions.
- **Escalation paths**: Safety-class complaints automatically route to Regulatory Affairs.

## Observability

- Azure Monitor / Application Insights wired via `azure-monitor-opentelemetry`.
- Structlog JSON logging with request-level context.
- Each FastAPI app exposes `/healthz`.

## Supply Chain

- Lockfile-based installs via `uv sync --extra dev`.
- CI runs `ruff`, `mypy`, `pytest`, and `az bicep build` on every PR.
