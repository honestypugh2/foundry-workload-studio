# Foundry Workload Studio — Frontend

A unified explorer for every Foundry-powered use case in this repo. Built with
**React 19 + TypeScript + Vite** and powered by the unified FastAPI gateway in
[`src/gateway`](../src/gateway). Adding a new use case to the backend
(`src/gateway/registry.py`) makes it appear in the sidebar automatically — the
UI is registry-driven.

## Features

- **Use-case explorer** — sidebar populated from `/api/usecases`. Each use case
  ships a sample request, an editable JSON request body, and a Run button.
- **Azure services panel** — pulled from `/api/azure-services` so the catalog
  of backing Azure services (Foundry, AI Search, Cosmos DB, Key Vault,
  Container Apps, APIM, Monitor, Storage) is always rendered from the source
  of truth, with deep links to docs.
- **Trace + debug panel** — every run returns a `Trace` with timed agent
  steps, status, and per-step attributes (citations, severity, anomalies, …).
  Rendered as a timeline with relative-duration bars.
- **Workflow visualizer** — nodes and edges declared per use case in the
  registry are rendered left-to-right; nodes that fired during the most
  recent run are highlighted.
- **Modular** — no use-case logic lives in the frontend. New use cases are
  added by registering them in the gateway only.

## Stack

Only stable, latest-major versions; nothing extra installed.

| Package                  | Version |
|--------------------------|---------|
| react / react-dom        | ^19.0.0 |
| react-router-dom         | ^7.1.0  |
| @tanstack/react-query    | ^5.62.0 |
| vite                     | ^6.0.0  |
| @vitejs/plugin-react     | ^4.3.4  |
| typescript               | ^5.7.0  |

No CSS framework is required — styling is plain CSS with a single light/dark
theme driven by CSS custom properties.

## Run locally

In one terminal, start the unified gateway:

```bash
# from repo root, with the uv virtualenv active
uvicorn src.gateway.api:app --reload --port 8000
```

In another terminal, start Vite:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api/*` and `/healthz` to the
gateway, so the React app calls relative paths only.

## Scripts

| Command            | Description |
|--------------------|-------------|
| `npm run dev`      | Vite dev server with HMR + gateway proxy. |
| `npm run build`    | Type-check (`tsc -b`) then build to `dist/`. |
| `npm run preview`  | Serve the production build locally. |
| `npm run typecheck`| Type-check without emitting. |

## Layout

```
frontend/
├── index.html
├── public/favicon.svg
├── src/
│   ├── api/
│   │   ├── client.ts            # fetch wrapper around gateway endpoints
│   │   └── types.ts             # mirrors src/gateway Pydantic models
│   ├── components/
│   │   ├── AzureServicesPanel.tsx
│   │   ├── RequestEditor.tsx
│   │   ├── TracePanel.tsx
│   │   └── WorkflowPanel.tsx
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   └── UseCasePage.tsx
│   ├── App.tsx
│   ├── main.tsx
│   └── styles.css
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
└── package.json
```

## Adding a new use case

You only need to touch the backend:

1. Implement an agent function (e.g. in `src/<your_usecase>/agent.py`).
2. Register it in [`src/gateway/registry.py`](../src/gateway/registry.py) by
   adding a `UseCase` entry (slug, name, description, sample input, Azure
   services it touches, workflow nodes/edges, and a runner that records steps
   via `TraceRecorder`).
3. Restart the gateway. The frontend picks the new entry up on next load.

## Production deployment

The build output (`frontend/dist/`) is a static SPA. Two recommended hosts:

- **Azure Static Web Apps** — point at `frontend/` with `output_location: dist`
  and configure the API as the linked Container App that serves
  `src.gateway.api:app`.
- **Azure Container Apps (sidecar)** — serve `dist/` from an `nginx`
  container alongside the gateway, route `/api/*` to the gateway service.

In both cases set `VITE`-side environment variables only at build time; the
gateway URL is resolved relatively (no API base needed when colocated).
