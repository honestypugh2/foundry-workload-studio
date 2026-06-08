# User Guide

A practical guide to understanding, running, and extending **Foundry Workload Studio** — a reusable accelerator that powers four governed AI workloads on Microsoft Foundry through one shared architecture.

- New here? Start with [Mental model](#mental-model) and [Run it locally](#run-it-locally).
- Want to add a workload? Jump to [Add a new use case](#add-a-new-use-case).
- Deploying to Azure? See [Go live on Azure](#go-live-on-azure).

For the system architecture and data flows, see [architecture.md](architecture.md). For a guided demo, see [demo-script.md](demo-script.md).

---

## Mental model

Everything funnels through **one FastAPI gateway** (`src/gateway`) that the React **Explorer** UI (`frontend/`) talks to. The gateway holds a **registry** of use cases. Each use case is a thin function that:

1. Optionally **retrieves** grounding documents (Azure AI Search live, or a local folder offline).
2. Runs business logic and/or a **Foundry agent** call.
3. Returns a typed Pydantic result plus a **trace** (the step-by-step timeline the UI renders).

The same code runs in two modes with **no code changes** — only environment variables differ:

| Mode | Trigger | Behavior |
|---|---|---|
| **Offline / stub** | `ENVIRONMENT=dev` or `test`, or an `example.*` endpoint | Local folder retrieval, deterministic stub model calls, no Azure calls. Ideal for tests and demos. |
| **Live / Azure** | `ENVIRONMENT=demo`/`prod` + real endpoints | Foundry prompt agents, Azure AI Search, Blob Storage, Monitor. |

The switch logic lives in `is_foundry_configured()` ([src/common/foundry_agents.py](../src/common/foundry_agents.py)) and each agent's `_default_retriever()`.

---

## Where the "live" code is

| Concern | Location |
|---|---|
| **HTTP API the UI calls** | [src/gateway/api.py](../src/gateway/api.py) — endpoints `/healthz`, `/api/usecases`, `/api/usecases/{slug}`, `/api/usecases/{slug}/run`, `/api/azure-services`, `/api/status` |
| **Use-case catalog + runners** | [src/gateway/registry.py](../src/gateway/registry.py) — the single place that wires each workload, its sample input, workflow graph, and runner |
| **Foundry agent calls (the real model)** | [src/common/foundry_agents.py](../src/common/foundry_agents.py) — provisions and invokes prompt agents via the v2 Agents API + OpenAI Responses API |
| **Per-workload logic** | `src/hr_policy_assistant/`, `src/clinical_laser_assistant/`, `src/quality_complaint_triage/`, `src/maintenance_copilot/` |
| **Frontend** | [frontend/src/App.tsx](../frontend/src/App.tsx) and `frontend/src/pages`, `frontend/src/components` |

The four `src/<use_case>/api.py` files are **standalone single-workload FastAPI apps** (used by the demo script and E2E tests). The **gateway** is what the React app and screenshots use day-to-day.

---

## `src/common` — the shared toolkit

Every use case is intentionally thin because the reusable parts live here:

| Module | Responsibility |
|---|---|
| [config.py](../src/common/config.py) | Pydantic-Settings `Settings` loaded from env / `.env`. `get_settings()` is cached. Defines all Foundry/Search/Cosmos/Storage/Monitor settings and `environment`. |
| [models.py](../src/common/models.py) | All shared Pydantic schemas: `Citation`, `ChatRequest`/`ChatResponse`, `Complaint`/`ComplaintTriageResult` (+ `Severity`, `ComplaintCategory` enums), `TelemetryRecord`/`TelemetrySummary`, `MaintenanceRecommendation`. `extra="forbid"` everywhere for strict validation. |
| [retrieval.py](../src/common/retrieval.py) | The `Retriever` protocol with two implementations: `AzureSearchRetriever` (semantic search live) and `LocalFolderRetriever` (keyword search over `data/*.md` offline). |
| [grounded.py](../src/common/grounded.py) | `compose_grounded_answer()` — the reusable RAG composer. Runs safety → enforces "no citations ⇒ refuse" → calls the injected `model_call` → returns a `ChatResponse`. |
| [safety.py](../src/common/safety.py) | `check_safety()` — cheap deterministic pre-filter (prompt-injection, SSN, PHI hints). Returns a `ContentSafetyVerdict`. Production should layer Azure AI Content Safety on top. |
| [foundry_client.py](../src/common/foundry_client.py) | Credential + client factories: cached `DefaultAzureCredential`, `build_project_client()`, `build_search_client()`. |
| [foundry_agents.py](../src/common/foundry_agents.py) | The Foundry integration. `AGENT_SPECS` is the source of truth for the four agents shown in the portal. `ensure_agent()` is idempotent (create-on-missing, version-on-drift), `run_agent()` invokes via the OpenAI Responses API, and `make_model_call()` returns a `ModelCall` the agents plug into. |
| [telemetry.py](../src/common/telemetry.py) | `configure_telemetry()` — idempotent structured logging (structlog/JSON) + optional Azure Monitor OpenTelemetry exporter. `get_logger()`. |

**Key idea:** agents depend on the *interfaces* (`Retriever`, `ModelCall`) defined here, so tests inject deterministic stubs and production injects Foundry/Search — same code path.

---

## The four use cases

| Slug | Module | Pattern | Workflow nodes |
|---|---|---|---|
| `hr-policy-assistant` | `src/hr_policy_assistant` | Grounded RAG | request → safety_pre_check → retrieve → compose_answer → response |
| `clinical-laser-assistant` | `src/clinical_laser_assistant` | Grounded RAG + clinical guardrails | (same RAG workflow) |
| `quality-complaint-triage` | `src/quality_complaint_triage` | Structured-output agent | complaint → classify → extract_entities → route → response |
| `maintenance-copilot` | `src/maintenance_copilot` | Telemetry + RAG | request → load_telemetry → summarize → ground_recommendation → response |

Each module has:
- `agent.py` — the `SYSTEM_PROMPT` (reused verbatim by the Foundry agent spec) plus the entry function (`agent_answer` / `triage` / `recommend`) and an offline stub.
- `api.py` — a standalone FastAPI app wrapping that entry function.
- Maintenance also has `telemetry_grounding.py` (load telemetry from local JSON or Blob, `summarize`, anomaly detection).

> Note: the Maintenance Copilot grounds against the clinical/maintenance KB docs in `data/clinical/` (no separate `data/maintenance/` folder). This matches the `maintenance-kb` index built by `scripts/seed_search.py`.

---

## Scripts

| Script | What it does |
|---|---|
| `scripts/provision_foundry_agents.py` | Idempotently creates the four prompt agents in your Foundry project (v2 Agents API). Run after `azd up` or whenever system prompts change. |
| `scripts/seed_search.py` | Creates the `hr-policies`, `clinical-laser`, and `maintenance-kb` Azure AI Search indexes (with a `default` semantic config) and uploads the `data/**.md` documents. |
| `scripts/seed_telemetry.py` | Uploads `data/telemetry/device_telemetry.json` to the `telemetry` Blob container the Maintenance Copilot reads live. |
| `scripts/run_all_e2e.py` | Runs all four end-to-end scripts with rich terminal output and an aggregate PASS/FAIL summary. The single "does the whole factory work?" command. |
| `scripts/e2e_hr.py`, `e2e_clinical.py`, `e2e_complaint_triage.py`, `e2e_maintenance.py` | Per-use-case end-to-end exercises (importable `main()` returning an exit code). |
| `scripts/debug.py` | Terminal logging helpers (`section`, `kv`, `log_response`, …) shared by the E2E scripts and `tests/test_e2e.py`. |
| `scripts/azd-postprovision.sh` | azd `postprovision` hook — writes provisioned endpoints into `.env` so the gateway/tests pick them up automatically. |

---

## Run it locally

### Prerequisites
- Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/)
- Node.js (for the frontend)

### One-time setup
```bash
uv sync --extra dev          # creates .venv and installs deps
cd frontend && npm install   # frontend deps
cd ..
```

### Start the full stack (gateway + Explorer UI)
```bash
./start.sh      # backend on :8000, frontend on :5173, logs in logs/
# open http://localhost:5173
./stop.sh       # when done
```
Without a `.env` (or with `ENVIRONMENT=dev`), the stack runs in **offline stub mode** — fully functional, no Azure needed.

### Run a single workload API
```bash
uv run uvicorn src.hr_policy_assistant.api:app --reload --port 8001
# then POST to http://localhost:8001/chat  (see http://localhost:8001/docs)
```

### Verify everything
```bash
uv run pytest                  # unit + integration (35 tests, offline)
uv run python scripts/run_all_e2e.py   # end-to-end, human-readable
uv run ruff check .            # lint
uv run mypy src                # type-check
```

---

## Go live on Azure

1. **Provision infra** (subscription-scoped Bicep, WAF-aligned):
   ```bash
   az deployment sub create --location eastus2 \
     --template-file infra/main.bicep \
     --parameters infra/environments/demo.bicepparam
   ```
   Or use `azd up` (azure.yaml wires the Bicep + the postprovision hook).
2. **Populate `.env`** with the real endpoints (the azd hook does this automatically; otherwise copy `.env.example`). Set `ENVIRONMENT=demo` or `prod`.
3. **Provision the agents:** `uv run python scripts/provision_foundry_agents.py`
4. **Seed data:** `uv run python scripts/seed_search.py && uv run python scripts/seed_telemetry.py`
5. **Restart** the stack — `/api/status` should now report Foundry **live** and the UI banner flips to "LIVE — Azure".

The `/api/status` endpoint probes each service and is the fastest way to confirm what's actually wired.

---

## Add a new use case

Adding a workload is deliberately cheap — the UI discovers it automatically via `/api/usecases`.

1. **Create the module** `src/my_use_case/agent.py` with a `SYSTEM_PROMPT` and an entry function that returns a Pydantic model.
2. **(Optional) Register a Foundry agent** by adding an `AgentSpec` to `AGENT_SPECS` in `src/common/foundry_agents.py` (set `response_format="json_object"` for structured output).
3. **Wire it into the registry** — add a `UseCase` entry in `src/gateway/registry.py` with a `slug`, `sample_input`, `azure_services`, a `TraceWorkflow`, and a `runner(payload, recorder)` function that records steps via `recorder.step(...)`.
4. **Add tests** under `tests/` and an optional `scripts/e2e_my_use_case.py`.

No frontend changes are required — the Explorer renders the new card, workflow, and trace from the registry metadata.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| UI shows "No use cases registered" | Page loaded before the backend was ready. Reload after `http://localhost:8000/healthz` returns 200. |
| Banner says "offline" though Azure is deployed | `ENVIRONMENT` is still `dev`, or an endpoint still contains `example`. Check `.env` and `/api/status`. |
| Foundry probe `error` on `/api/status` | Not signed in or missing RBAC. Run `az login`; ensure the principal has the **Azure AI User** role on the project. |
| Agents not visible in the portal | Run `scripts/provision_foundry_agents.py`; confirm `FOUNDRY_PROJECT_ENDPOINT` points at the **project** (`…/api/projects/<name>`). |
| Live answers ungrounded | Run `scripts/seed_search.py`; verify index names match the `AZURE_SEARCH_*_INDEX` settings. |
| Tests touching Azure | They shouldn't — `tests/conftest.py` forces `ENVIRONMENT=test` and example endpoints. Keep new code behind the `is_foundry_configured()` gate. |
