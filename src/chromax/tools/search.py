"""Semantic search tool for Chromax — queries the local ChromaDB vector store."""

from __future__ import annotations

from dataclasses import dataclass

from chromax.indexer.indexer import Indexer


@dataclass
class SearchResult:
    content: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    score: float  # lower = more similar (L2 distance)

    @property
    def citation(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


def search_codebase(query: str, repo: str, n_results: int = 5) -> list[SearchResult]:
    """Search indexed codebase chunks by semantic similarity.

    Args:
        query: Natural language search query.
        repo: Repository in 'owner/name' format (must be indexed first).
        n_results: Number of results to return.

    Returns:
        List of SearchResult sorted by relevance (most relevant first).
    """
    indexer = Indexer(repo)
    if indexer.chunk_count() == 0:
        return []

    raw = indexer._collection.query(
        query_texts=[query],
        n_results=min(n_results, indexer.chunk_count()),
        include=["documents", "metadatas", "distances"],
    )

    results: list[SearchResult] = []
    for doc, meta, dist in zip(
        raw["documents"][0],
        raw["metadatas"][0],
        raw["distances"][0],
    ):
        results.append(SearchResult(
            content=doc,
            file_path=meta["file_path"],
            language=meta["language"],
            start_line=int(meta["start_line"]),
            end_line=int(meta["end_line"]),
            score=dist,
        ))

    return results
