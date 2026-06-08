"""Debug + structured logging helpers for end-to-end scripts.

Designed for human readability in a terminal. Output is plain text with
ANSI colors when the stream is a TTY; otherwise colors are stripped so
logs stay clean in CI.

Usage:
    from scripts.debug import section, kv, log_citations, log_response, run_step

    with section("HR Policy Assistant"):
        log_request("How many PTO days?")
        resp = agent_answer("How many PTO days?")
        log_response(resp)
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from src.common.models import (
    ChatResponse,
    Citation,
    ComplaintTriageResult,
    MaintenanceRecommendation,
    TelemetrySummary,
)

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def _bold(t: str) -> str:
    return _c(t, "1")


def _dim(t: str) -> str:
    return _c(t, "2")


def _cyan(t: str) -> str:
    return _c(t, "36")


def _green(t: str) -> str:
    return _c(t, "32")


def _yellow(t: str) -> str:
    return _c(t, "33")


def _red(t: str) -> str:
    return _c(t, "31")


def _magenta(t: str) -> str:
    return _c(t, "35")


# ---------- structured printers ----------


@contextmanager
def section(title: str) -> Iterator[None]:
    """Visually framed section with timing information."""
    bar = "═" * max(8, 64 - len(title))
    print()
    print(_cyan(f"╔══ {_bold(title)} {bar}"))
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        print(_cyan(f"╚══ done in {elapsed_ms:.1f} ms"))


@contextmanager
def step(label: str) -> Iterator[None]:
    print(_dim(f"  → {label} ..."))
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        print(_dim(f"  ← {label} ({elapsed_ms:.1f} ms)"))


def kv(key: str, value: Any) -> None:
    """Print a key/value pair with consistent formatting."""
    if isinstance(value, (dict, list)):
        rendered = json.dumps(value, indent=2, default=str)
        print(f"  {_bold(key)}:")
        for line in rendered.splitlines():
            print(f"    {line}")
    else:
        print(f"  {_bold(key)}: {value}")


def log_request(question: str, **extra: Any) -> None:
    print(_yellow(f"  ▶ request: {question!r}"))
    for k, v in extra.items():
        kv(k, v)


def log_citations(citations: Iterable[Citation]) -> None:
    items = list(citations)
    if not items:
        print(_red("  ⚠ no citations retrieved"))
        return
    print(_green(f"  ✓ {len(items)} citation(s) retrieved:"))
    for i, c in enumerate(items, start=1):
        score = f"{c.score:.2f}" if c.score is not None else "n/a"
        print(f"    [{i}] {_bold(c.title)} (id={c.source_id}, score={score})")
        snippet = c.snippet.strip().replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:140] + "…"
        print(_dim(f"        {snippet}"))


def log_response(resp: ChatResponse) -> None:
    color = _green if resp.grounded else _red
    print(color(f"  ◀ grounded={resp.grounded}, escalation={resp.escalation_recommended}"))
    print(_magenta("  answer:"))
    for line in resp.answer.splitlines():
        print(f"    {line}")
    log_citations(resp.citations)


def log_triage(result: ComplaintTriageResult) -> None:
    print(_magenta("  ◀ triage:"))
    kv("complaint_id", result.complaint_id)
    kv("category", result.category.value)
    kv("severity", result.severity.value)
    kv("suggested_route", result.suggested_route)
    kv("requires_escalation", result.requires_escalation)
    kv("summary", result.summary)
    kv("extracted_entities", result.extracted_entities)


def log_telemetry_summary(summary: TelemetrySummary) -> None:
    print(_magenta("  ◀ telemetry summary:"))
    kv("device_id", summary.device_id)
    kv("window_hours", summary.metric_window_hours)
    kv("metrics", summary.metrics)
    if summary.anomalies:
        for a in summary.anomalies:
            print(_red(f"    ! anomaly: {a}"))
    else:
        print(_green("    ✓ no anomalies"))


def log_maintenance(rec: MaintenanceRecommendation) -> None:
    print(_magenta("  ◀ maintenance recommendation:"))
    kv("device_id", rec.device_id)
    kv("confidence", rec.confidence)
    kv("reasoning", rec.reasoning)
    print(_bold("  recommended actions:"))
    for i, a in enumerate(rec.recommended_actions, start=1):
        print(f"    {i}. {a}")
    log_citations(rec.citations)


# ---------- runner harness ----------


@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""


def run_step(name: str, fn) -> StepResult:
    try:
        fn()
    except AssertionError as exc:
        print(_red(f"  ✗ FAIL: {name} — {exc}"))
        return StepResult(name=name, passed=False, detail=str(exc))
    except Exception as exc:  # pragma: no cover — defensive for ad-hoc runs
        print(_red(f"  ✗ ERROR: {name} — {exc!r}"))
        return StepResult(name=name, passed=False, detail=repr(exc))
    print(_green(f"  ✓ pass: {name}"))
    return StepResult(name=name, passed=True)


def print_summary(results: list[StepResult]) -> int:
    print()
    total = len(results)
    failed = [r for r in results if not r.passed]
    if not failed:
        print(_green(f"━━━ ALL {total} CHECKS PASSED ━━━"))
        return 0
    print(_red(f"━━━ {len(failed)}/{total} CHECKS FAILED ━━━"))
    for r in failed:
        print(_red(f"  ✗ {r.name}: {r.detail}"))
    return 1
