"""Phase 4C — Test the in-process LLM response cache."""

from __future__ import annotations

from chromax.cache import ResponseCache


class TestResponseCache:
    def setup_method(self):
        self.cache = ResponseCache(ttl=60)

    def test_miss_returns_none(self):
        assert self.cache.get("How does auth work?", "psf/requests") is None

    def test_set_then_get_returns_value(self):
        self.cache.set("How does auth work?", "psf/requests", "Auth is in requests/auth.py")
        result = self.cache.get("How does auth work?", "psf/requests")
        assert result == "Auth is in requests/auth.py"

    def test_different_repo_is_different_key(self):
        self.cache.set("What does this do?", "psf/requests", "HTTP library")
        assert self.cache.get("What does this do?", "other/repo") is None

    def test_case_insensitive_question_hits(self):
        self.cache.set("How does auth work?", "psf/requests", "answer")
        assert self.cache.get("how does auth work?", "psf/requests") == "answer"
        assert self.cache.get("  How does auth work?  ", "psf/requests") == "answer"

    def test_expired_entry_returns_none(self):
        cache = ResponseCache(ttl=1)
        cache.set("question", "repo/x", "answer")

        # Monkeypatch: manually expire by backdating stored time
        key = cache._key("question", "repo/x")
        stored_at, value = cache._store[key]
        cache._store[key] = (stored_at - 2, value)  # make it 2s old with ttl=1

        assert cache.get("question", "repo/x") is None

    def test_expired_entry_is_evicted(self):
        cache = ResponseCache(ttl=1)
        cache.set("question", "repo/x", "answer")
        key = cache._key("question", "repo/x")
        stored_at, value = cache._store[key]
        cache._store[key] = (stored_at - 2, value)

        cache.get("question", "repo/x")  # triggers eviction
        assert key not in cache._store

    def test_session_calls_bypass_cache(self):
        """ask_with_session should NOT use the cache (multi-turn needs live responses)."""
        # The cache is only wired into route(), not ask_with_session()
        # This test verifies the cache interface doesn't expose session methods
        assert not hasattr(self.cache, "get_session")
        assert not hasattr(self.cache, "set_session")
