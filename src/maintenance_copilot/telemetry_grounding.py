"""Telemetry summarization for the Maintenance Copilot.

Reads device telemetry (JSON list of records) and produces a `TelemetrySummary`
flagging anomalies that the agent then grounds against the maintenance KB.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable
from pathlib import Path

from src.common.models import TelemetryRecord, TelemetrySummary

# Conservative thresholds — tune per device family.
_THRESHOLDS: dict[str, tuple[float, float]] = {
    "cooling_temp_c": (15.0, 28.0),
    "pulse_energy_j": (0.8, 1.2),
    "pump_pressure_psi": (40.0, 90.0),
    "vibration_g": (0.0, 0.6),
}


def load_records(path: Path | str) -> list[TelemetryRecord]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [TelemetryRecord.model_validate(item) for item in raw]


def load_records_from_blob(
    *,
    account: str,
    container: str = "telemetry",
    blob: str = "device_telemetry.json",
) -> list[TelemetryRecord]:
    """Load telemetry from Blob Storage using DefaultAzureCredential.

    Requires ``Storage Blob Data Reader`` (or Contributor) on the account.
    """
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobClient

    url = f"https://{account}.blob.core.windows.net/{container}/{blob}"
    client = BlobClient.from_blob_url(url, credential=DefaultAzureCredential())
    raw = json.loads(client.download_blob().readall())
    return [TelemetryRecord.model_validate(item) for item in raw]


def summarize(
    records: Iterable[TelemetryRecord],
    *,
    device_id: str,
    window_hours: int = 24,
) -> TelemetrySummary:
    by_metric: dict[str, list[float]] = {}
    for r in records:
        if r.device_id != device_id:
            continue
        by_metric.setdefault(r.metric, []).append(r.value)

    metrics: dict[str, float] = {}
    anomalies: list[str] = []
    for metric, values in by_metric.items():
        if not values:
            continue
        avg = statistics.fmean(values)
        max_v = max(values)
        min_v = min(values)
        metrics[f"{metric}_avg"] = round(avg, 3)
        metrics[f"{metric}_max"] = round(max_v, 3)
        metrics[f"{metric}_min"] = round(min_v, 3)
        lo, hi = _THRESHOLDS.get(metric, (float("-inf"), float("inf")))
        if avg < lo or avg > hi:
            anomalies.append(
                f"{metric} avg={avg:.2f} outside expected [{lo}, {hi}]"
            )
        elif max_v > hi:
            anomalies.append(
                f"{metric} max={max_v:.2f} exceeded upper bound {hi}"
            )
        elif min_v < lo:
            anomalies.append(
                f"{metric} min={min_v:.2f} below lower bound {lo}"
            )

    if not metrics:
        # Ensure validator passes; signal no telemetry observed.
        metrics = {"records_observed": 0.0}
        anomalies.append("no_telemetry_for_device")

    return TelemetrySummary(
        device_id=device_id,
        metric_window_hours=window_hours,
        metrics=metrics,
        anomalies=anomalies,
    )
