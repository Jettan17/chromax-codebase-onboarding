"""Phase 2A — Test the Chromax indexer pipeline."""

from __future__ import annotations

import pytest
from chromax.indexer.chunker import chunk_file, is_text_file, language_from_path
from chromax.indexer.indexer import Indexer

TEST_REPO = "psf/requests"


# ---------- Chunker unit tests (no network) ----------

class TestIsTextFile:
    def test_python_file_accepted(self):
        assert is_text_file("src/auth.py", 1000) is True

    def test_large_file_rejected(self):
        assert is_text_file("big.py", 200_000) is False

    def test_binary_extension_rejected(self):
        assert is_text_file("image.png", 100) is False

    def test_markdown_accepted(self):
        assert is_text_file("README.md", 5000) is True


class TestLanguageFromPath:
    def test_python(self):
        assert language_from_path("src/main.py") == "python"

    def test_typescript(self):
        assert language_from_path("app/index.ts") == "typescript"

    def test_unknown_extension(self):
        assert language_from_path("Makefile") == "text"


class TestChunkFile:
    PYTHON_CONTENT = "\n".join([
        "def foo():",
        "    return 1",
        "",
        "def bar():",
        "    return 2",
        "",
        "class Baz:",
        "    def method(self):",
        "        pass",
    ])

    def test_returns_chunks(self):
        chunks = chunk_file(self.PYTHON_CONTENT, "src/example.py", "owner/repo")
        assert len(chunks) >= 1

    def test_chunk_metadata(self):
        chunks = chunk_file(self.PYTHON_CONTENT, "src/example.py", "owner/repo")
        for chunk in chunks:
            assert chunk.file_path == "src/example.py"
            assert chunk.language == "python"
            assert chunk.repo == "owner/repo"
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_empty_file_returns_no_chunks(self):
        chunks = chunk_file("", "empty.py", "owner/repo")
        assert chunks == []

    def test_chunks_cover_content(self):
        chunks = chunk_file(self.PYTHON_CONTENT, "src/example.py", "owner/repo")
        combined = "\n".join(c.content for c in chunks)
        # Every def/class should appear somewhere in the chunks
        assert "def foo" in combined
        assert "def bar" in combined
        assert "class Baz" in combined


# ---------- Indexer integration tests (real network) ----------
# These tests share one index run via a module-level fixture to avoid
# re-fetching psf/requests from GitHub on every test.

import pytest

@pytest.fixture(scope="module")
def indexed_repo():
    """Index psf/requests once and share across all tests in this module."""
    indexer = Indexer(TEST_REPO)
    stats = indexer.index()
    return indexer, stats


class TestIndexer:
    def test_index_creates_chunks(self, indexed_repo):
        indexer, stats = indexed_repo
        assert indexer.chunk_count() > 50, "Expected more than 50 chunks"

    def test_chunk_metadata_fields(self, indexed_repo):
        indexer, _ = indexed_repo
        results = indexer._collection.get(limit=5, include=["metadatas"])
        for meta in results["metadatas"]:
            assert "file_path" in meta
            assert "language" in meta
            assert "start_line" in meta
            assert "end_line" in meta
            assert "repo" in meta

    def test_binary_files_skipped(self, indexed_repo):
        _, stats = indexed_repo
        assert stats["files_skipped"] > 0, "Some files should be skipped"

    def test_index_is_idempotent(self, indexed_repo):
        indexer, _ = indexed_repo
        ids_first = set(indexer._collection.get()["ids"])
        stats2 = indexer.index()  # second run — psf/requests already in DB
        ids_second = set(indexer._collection.get()["ids"])
        assert ids_first == ids_second, "Re-indexing should not add duplicate chunks"
        assert stats2["chunks_added"] == 0, "No new chunks should be added on second run"
