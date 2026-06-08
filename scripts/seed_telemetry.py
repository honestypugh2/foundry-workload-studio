"""Seed Blob Storage with the device telemetry JSON the maintenance copilot reads.

Creates the ``telemetry`` container (idempotently) on
``AZURE_STORAGE_ACCOUNT`` and uploads ``data/telemetry/device_telemetry.json``
as ``device_telemetry.json``.

Usage::

    uv run python scripts/seed_telemetry.py

Requires ``Storage Blob Data Contributor`` on the account (already granted by
infra/modules/storage.bicep to the deploying principal).
"""

from __future__ import annotations

import sys
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from src.common.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_FILE = ROOT / "data" / "telemetry" / "device_telemetry.json"
CONTAINER = "telemetry"
BLOB_NAME = "device_telemetry.json"


def main() -> int:
    settings = get_settings()
    account = settings.azure_storage_account
    if not account:
        print("AZURE_STORAGE_ACCOUNT is not set; aborting.", file=sys.stderr)
        return 2
    if not TELEMETRY_FILE.exists():
        print(f"Missing telemetry file: {TELEMETRY_FILE}", file=sys.stderr)
        return 2

    url = f"https://{account}.blob.core.windows.net"
    svc = BlobServiceClient(account_url=url, credential=DefaultAzureCredential())

    try:
        svc.create_container(CONTAINER)
        print(f"[{CONTAINER}] container created")
    except ResourceExistsError:
        print(f"[{CONTAINER}] container exists")

    blob = svc.get_blob_client(container=CONTAINER, blob=BLOB_NAME)
    blob.upload_blob(TELEMETRY_FILE.read_bytes(), overwrite=True)
    print(f"[{CONTAINER}/{BLOB_NAME}] uploaded {TELEMETRY_FILE.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
