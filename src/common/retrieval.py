"""Generic retrieval abstraction usable by all RAG use cases.

A `Retriever` is any callable returning a list of `Citation` for a query.
Concrete `AzureSearchRetriever` queries Azure AI Search; `LocalFolderRetriever`
loads markdown from disk for offline tests / dev.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from src.common.foundry_client import build_search_client
from src.common.models import Citation


class Retriever(Protocol):
    def retrieve(self, query: str, *, top: int = 5) -> list[Citation]: ...


class AzureSearchRetriever:
    """Hits Azure AI Search using semantic ranking when available."""

    def __init__(self, index_name: str) -> None:
        self._index = index_name
        self._client = build_search_client(index_name)

    def retrieve(self, query: str, *, top: int = 5) -> list[Citation]:
        results = self._client.search(
            search_text=query,
            top=top,
            query_type="semantic",
            semantic_configuration_name="default",
            query_caption="extractive",
        )
        out: list[Citation] = []
        for r in results:
            out.append(
                Citation(
                    source_id=str(r.get("id") or r.get("source_id") or ""),
                    title=str(r.get("title") or r.get("source_id") or "untitled"),
                    url=r.get("url"),
                    snippet=str(r.get("content") or r.get("snippet") or "")[:1500],
                    score=(
                        min(1.0, float(r["@search.score"]) / 5.0)
                        if "@search.score" in r
                        else None
                    ),
                )
            )
        return out


_STOPWORDS = frozenset(
    {
        "the", "and", "for", "that", "this", "with", "from", "have", "has",
        "are", "was", "were", "but", "not", "you", "your", "how", "what",
        "when", "why", "who", "which", "does", "did", "can", "could", "would",
        "should", "there", "their", "them", "its", "into", "about", "any",
        "all", "some", "more", "than", "then", "also", "may", "will", "just",
        "only", "over", "under", "per", "out", "off", "new", "old", "get",
        "got", "use", "used", "using", "exist", "exists", "topic", "do",
    }
)


class LocalFolderRetriever:
    """Naive keyword retriever over a folder of markdown files (offline / tests)."""

    def __init__(self, folder: Path | str) -> None:
        self._folder = Path(folder)
        self._docs: list[tuple[str, str]] = []  # (name, text)
        if self._folder.exists():
            for md in sorted(self._folder.glob("*.md")):
                self._docs.append((md.stem, md.read_text(encoding="utf-8")))

    @staticmethod
    def _score(text: str, terms: Iterable[str]) -> int:
        lowered = text.lower()
        return sum(lowered.count(t) for t in terms)

    def retrieve(self, query: str, *, top: int = 5) -> list[Citation]:
        terms = [
            t for t in query.lower().split()
            if len(t) > 2 and t not in _STOPWORDS
        ]
        if not terms:
            return []
        scored = [
            (name, text, self._score(text, terms))
            for name, text in self._docs
        ]
        scored = [s for s in scored if s[2] > 0]
        scored.sort(key=lambda s: s[2], reverse=True)
        out: list[Citation] = []
        for name, text, score in scored[:top]:
            out.append(
                Citation(
                    source_id=name,
                    title=name.replace("_", " ").title(),
                    snippet=text[:1500],
                    score=min(1.0, score / 10.0),
                )
            )
        return out
