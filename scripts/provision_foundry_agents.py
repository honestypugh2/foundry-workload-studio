#!/usr/bin/env python
"""Provision (idempotent) the four Foundry persistent agents.

Uses the **v2 Agents API** (`azure-ai-projects` AgentsOperations) so the
agents appear in ai.azure.com → Project → **Agents**.

Run once after `azd up` (or any time the system prompts change):

    python -m scripts.provision_foundry_agents
"""

from __future__ import annotations

import logging
import sys

from src.common.config import get_settings
from src.common.foundry_agents import is_foundry_configured, provision_all


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg = get_settings()
    if not is_foundry_configured(cfg):
        print(
            f"Foundry is not configured (environment={cfg.environment}, "
            f"endpoint={cfg.foundry_project_endpoint}). "
            "Set FOUNDRY_PROJECT_ENDPOINT to a real project before provisioning.",
            file=sys.stderr,
        )
        return 2

    print(f"Provisioning agents against {cfg.foundry_project_endpoint}")
    print(f"Model deployment: {cfg.foundry_model_deployment}\n")
    names = provision_all(cfg)
    width = max(len(k) for k in names)
    for key, name in names.items():
        print(f"  {key.ljust(width)}  {name}")
    print(f"\nProvisioned {len(names)} agents. View them in the Foundry portal → Agents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

