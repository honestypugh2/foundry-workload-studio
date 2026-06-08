"""Run all four end-to-end use case scripts and aggregate results.

This is the single command to verify the entire factory works end-to-end
with verbose, debug-friendly output. Exits non-zero if any check fails.

    uv run python scripts/run_all_e2e.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import e2e_clinical, e2e_complaint_triage, e2e_hr, e2e_maintenance
from scripts.debug import section

USE_CASES = [
    ("HR Policy Assistant", e2e_hr.main),
    ("Clinical Laser Assistant", e2e_clinical.main),
    ("Quality Complaint Triage", e2e_complaint_triage.main),
    ("Preventative Maintenance Copilot", e2e_maintenance.main),
]


def main() -> int:
    overall_status = 0
    summary: list[tuple[str, int]] = []

    for name, runner in USE_CASES:
        with section(f"USE CASE: {name}"):
            rc = runner()
        summary.append((name, rc))
        if rc != 0:
            overall_status = rc

    print()
    print("══════════════════════════════════════════════════")
    print(" AGGREGATE END-TO-END SUMMARY")
    print("══════════════════════════════════════════════════")
    for name, rc in summary:
        status = "PASS" if rc == 0 else "FAIL"
        print(f"  [{status}] {name}")
    print("══════════════════════════════════════════════════")
    return overall_status


if __name__ == "__main__":
    raise SystemExit(main())
