"""Chromax indexer — fetches a GitHub repo and stores chunks in ChromaDB."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from chromax.indexer.chunker import Chunk, chunk_file, is_text_file
from chromax.tools.github import _get_client

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".chromax" / "db"


def _collection_name(repo: str) -> str:
    """ChromaDB collection name derived from repo slug."""
    safe = repo.replace("/", "__").replace("-", "_")
    return f"chromax__{safe}"


def _chunk_id(chunk: Chunk) -> str:
    """Stable ID for a chunk based on content hash."""
    digest = hashlib.sha256(chunk.content.encode()).hexdigest()[:16]
    return f"{chunk.file_path}:{chunk.start_line}:{digest}"


class Indexer:
    """Fetches a GitHub repo via API, chunks files, and stores in ChromaDB."""

    def __init__(self, repo: str):
        self.repo = repo
        self._client = chromadb.PersistentClient(path=str(DB_PATH))
        self._ef = ONNXMiniLM_L6_V2()
        self._collection = self._client.get_or_create_collection(
            name=_collection_name(repo),
            embedding_function=self._ef,
            metadata={"repo": repo},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self) -> dict:
        """Run full indexing pipeline.

        Returns:
            dict with keys: files_fetched, files_skipped, chunks_added, chunks_skipped
        """
        logger.info("Fetching file list for %s", self.repo)
        file_entries = self._list_files()

        stats = {"files_fetched": 0, "files_skipped": 0, "chunks_added": 0, "chunks_skipped": 0}
        all_chunks: list[Chunk] = []

        for path, size in file_entries:
            if not is_text_file(path, size):
                stats["files_skipped"] += 1
                logger.debug("Skipping %s (size=%d)", path, size)
                continue

            content = self._fetch_file(path)
            if content is None:
                stats["files_skipped"] += 1
                continue

            chunks = chunk_file(content, path, self.repo)
            all_chunks.extend(chunks)
            stats["files_fetched"] += 1
            logger.debug("Chunked %s → %d chunks", path, len(chunks))

        added, skipped = self._store_chunks(all_chunks)
        stats["chunks_added"] = added
        stats["chunks_skipped"] = skipped
        return stats

    def chunk_count(self) -> int:
        """Return number of chunks currently stored for this repo."""
        return self._collection.count()

    def collection_metadata(self) -> dict:
        return self._collection.metadata or {}

    def query(self, query_text: str, n_results: int = 5) -> dict:
        """Run a semantic similarity query against the indexed chunks.

        Returns the raw ChromaDB response dict with keys:
        ``documents``, ``metadatas``, ``distances``.
        """
        count = self._collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return self._collection.query(
            query_texts=[query_text],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _list_files(self) -> list[tuple[str, int]]:
        """Return list of (path, size_bytes) for all files in the repo."""
        g = _get_client()
        r = g.get_repo(self.repo)
        tree = r.get_git_tree(r.default_branch, recursive=True)
        return [
            (element.path, element.size or 0)
            for element in tree.tree
            if element.type == "blob"
        ]

    def _fetch_file(self, path: str) -> str | None:
        """Fetch raw file content. Returns None on error."""
        from chromax.tools.github import get_file_content
        result = get_file_content(self.repo, path)
        if result.startswith("Error:"):
            logger.warning("Could not fetch %s: %s", path, result)
            return None
        return result

    def _store_chunks(self, chunks: list[Chunk]) -> tuple[int, int]:
        """Upsert chunks into ChromaDB. Returns (added, skipped) counts."""
        if not chunks:
            return 0, 0

        ids = [_chunk_id(c) for c in chunks]
        existing = set(self._collection.get(ids=ids)["ids"])

        new_chunks = [(cid, c) for cid, c in zip(ids, chunks) if cid not in existing]
        if not new_chunks:
            return 0, len(chunks)

        new_ids, new_c = zip(*new_chunks)
        self._collection.add(
            ids=list(new_ids),
            documents=[c.content for c in new_c],
            metadatas=[{
                "file_path": c.file_path,
                "language": c.language,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "repo": c.repo,
            } for c in new_c],
        )
        return len(new_ids), len(chunks) - len(new_ids)
