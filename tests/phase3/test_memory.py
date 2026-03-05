"""Phase 3B — Test conversation memory and SHA-based index tracking."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from chromax.agents.supervisor import ask_with_session
from chromax.indexer.indexer import Indexer
from chromax.memory.conversation import clear_session, load_session, save_session

TEST_REPO = "psf/requests"


# ---------- Conversation memory ----------

class TestSessionIdValidation:
    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="Invalid session_id"):
            load_session("../../etc/passwd")

    def test_dotdot_rejected(self):
        with pytest.raises(ValueError, match="Invalid session_id"):
            load_session("../config")

    def test_slash_rejected(self):
        with pytest.raises(ValueError, match="Invalid session_id"):
            load_session("a/b")

    def test_valid_ids_accepted(self):
        # Should not raise (file won't exist, returns [])
        assert load_session("chat-abc123") == []
        assert load_session("my_session") == []


class TestConversationPersistence:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        """Messages saved to disk are loaded back correctly."""
        from chromax.memory import conversation as conv_mod
        monkeypatch.setattr(conv_mod, "SESSIONS_DIR", tmp_path)

        session_id = "test-roundtrip"
        messages = [
            {"role": "human", "content": "Hello"},
            {"role": "ai", "content": "Hi there!"},
        ]
        save_session(session_id, messages)
        loaded = load_session(session_id)
        assert loaded == messages

    def test_load_nonexistent_returns_empty(self, tmp_path, monkeypatch):
        from chromax.memory import conversation as conv_mod
        monkeypatch.setattr(conv_mod, "SESSIONS_DIR", tmp_path)
        assert load_session("does-not-exist") == []

    def test_clear_removes_session(self, tmp_path, monkeypatch):
        from chromax.memory import conversation as conv_mod
        monkeypatch.setattr(conv_mod, "SESSIONS_DIR", tmp_path)

        save_session("to-clear", [{"role": "human", "content": "hi"}])
        clear_session("to-clear")
        assert load_session("to-clear") == []


class TestSessionMemory:
    def test_session_remembers_context(self):
        """Second question in session can reference context from the first."""
        from groq import RateLimitError
        session_id = f"test-{uuid.uuid4().hex[:8]}"
        try:
            answer1 = ask_with_session(
                "What is the main purpose of the requests library?",
                TEST_REPO,
                session_id,
            )
            assert isinstance(answer1, str) and len(answer1) > 20

            answer2 = ask_with_session(
                "Summarise what you just told me in one sentence.",
                TEST_REPO,
                session_id,
            )
            assert isinstance(answer2, str) and len(answer2) > 10
        except RateLimitError:
            pytest.skip("Groq daily token limit reached — re-run tomorrow")
        finally:
            clear_session(session_id)


# ---------- SHA-based index tracking ----------

@pytest.fixture(scope="module")
def sha_indexed():
    """Index psf/requests once and return the indexer."""
    indexer = Indexer(TEST_REPO)
    stats = indexer.index()
    return indexer, stats


class TestSHATracking:
    def test_sha_stored_after_index(self, sha_indexed):
        indexer, _ = sha_indexed
        sha = indexer.collection_metadata().get("last_indexed_sha")
        assert sha is not None and len(sha) > 0

    def test_same_sha_short_circuits(self, sha_indexed):
        """Re-indexing at the same SHA returns immediately with 0 new chunks."""
        indexer, _ = sha_indexed
        stats = indexer.index()
        assert stats["chunks_added"] == 0
        # Short-circuit means files_fetched is also 0
        assert stats["files_fetched"] == 0

    def test_sha_change_triggers_full_pipeline(self, sha_indexed):
        """When the stored SHA differs from HEAD, the full index pipeline runs."""
        indexer, _ = sha_indexed
        original_metadata = dict(indexer.collection_metadata())

        # Force a SHA mismatch
        indexer._collection.modify(metadata={**original_metadata, "last_indexed_sha": "fake_sha"})

        try:
            with patch.object(indexer, "_list_files", return_value=[]) as mock_list:
                indexer.index()
                mock_list.assert_called_once()
        finally:
            # Restore original metadata
            indexer._collection.modify(metadata=original_metadata)
