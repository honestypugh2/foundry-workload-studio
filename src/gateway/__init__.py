"""Unified gateway exposing every use case behind a single API.

The gateway is the single entry point for the React frontend. It provides:

* A use-case registry (`/api/usecases`) the UI uses to render its sidebar.
* A catalog of backing Azure services (`/api/azure-services`).
* Per-use-case invocation endpoints (`/api/usecases/{slug}/run`) that wrap
  the underlying agent and return a synthesised trace alongside the result.
"""
