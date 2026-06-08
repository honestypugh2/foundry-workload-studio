"""End-to-end runnable scripts and shared debug helpers.

These scripts exercise each use case against the local sample data
(no Azure resources required) and print verbose, structured output so
operators can see exactly which retriever, citations, agent decisions,
and HTTP shapes are involved.

Run:
    uv run python scripts/run_all_e2e.py
    uv run python scripts/e2e_hr.py
    uv run python scripts/e2e_clinical.py
    uv run python scripts/e2e_complaint_triage.py
    uv run python scripts/e2e_maintenance.py
"""
