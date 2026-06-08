"""Seed Azure AI Search with the three indexes used by the live demo.

Creates (idempotently) the indexes ``hr-policies``, ``clinical-laser``, and
``maintenance-kb``, each with a ``default`` semantic configuration matching
``AzureSearchRetriever``, then uploads the markdown files under ``data/`` as
documents.

Usage::

    uv run python scripts/seed_search.py

Requires ``AZURE_SEARCH_ENDPOINT`` in environment / .env and the signed-in
principal to have ``Search Service Contributor`` + ``Search Index Data
Contributor`` on the search service (already granted by infra/modules/search.bicep).
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
)

from src.common.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


@dataclass(frozen=True)
class IndexPlan:
    name: str
    sources: tuple[Path, ...]


def _doc_id(source_id: str) -> str:
    # Search keys must match [A-Za-z0-9_\-=]; hash to keep things safe.
    return hashlib.sha1(source_id.encode("utf-8"), usedforsecurity=False).hexdigest()


def _build_index(name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="source_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="url", type=SearchFieldDataType.String, filterable=False),
        SearchField(
            name="tags",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True,
        ),
    ]
    semantic = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="source_id")],
                ),
            )
        ]
    )
    return SearchIndex(name=name, fields=fields, semantic_search=semantic)


def _read_doc(path: Path, *, tags: list[str]) -> dict:
    text = path.read_text(encoding="utf-8")
    title = path.stem.replace("_", " ").title()
    return {
        "id": _doc_id(path.stem),
        "source_id": path.stem,
        "title": title,
        "content": text,
        "url": f"file://{path.relative_to(ROOT)}",
        "tags": tags,
    }


def _plans() -> list[IndexPlan]:
    return [
        IndexPlan(
            name="hr-policies",
            sources=tuple(sorted((DATA / "hr").glob("*.md"))),
        ),
        IndexPlan(
            name="clinical-laser",
            sources=(
                DATA / "clinical" / "laser_product_guide.md",
                DATA / "clinical" / "operational_warnings.md",
            ),
        ),
        IndexPlan(
            name="maintenance-kb",
            sources=(
                DATA / "clinical" / "maintenance_weekly.md",
                DATA / "clinical" / "operational_warnings.md",
            ),
        ),
    ]


def main() -> int:
    settings = get_settings()
    endpoint = settings.azure_search_endpoint
    if "example" in endpoint:
        print(f"AZURE_SEARCH_ENDPOINT looks unset ({endpoint}); aborting.", file=sys.stderr)
        return 2

    cred = DefaultAzureCredential()
    idx_client = SearchIndexClient(endpoint=endpoint, credential=cred)

    for plan in _plans():
        missing = [s for s in plan.sources if not s.exists()]
        if missing:
            print(f"[{plan.name}] skipping missing sources: {missing}", file=sys.stderr)
            continue

        idx_client.create_or_update_index(_build_index(plan.name))
        print(f"[{plan.name}] index ready")

        docs = [_read_doc(p, tags=[plan.name]) for p in plan.sources]
        with SearchClient(endpoint=endpoint, index_name=plan.name, credential=cred) as sc:
            result = sc.merge_or_upload_documents(documents=docs)
        ok = sum(1 for r in result if r.succeeded)
        print(f"[{plan.name}] uploaded {ok}/{len(docs)} documents")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
