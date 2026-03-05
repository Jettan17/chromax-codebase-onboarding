"""In-process TTL cache for LLM responses.

Keyed by (repo, normalised_question). Avoids re-querying the LLM for identical
questions within the same process invocation. Cache is lost on process exit —
intentional for v0.1.0 (keeps it simple and avoids stale answers).
"""

from __future__ import annotations

import hashlib
import time

_DEFAULT_TTL = 3600  # 1 hour


class ResponseCache:
    """Thread-unsafe in-memory TTL cache for LLM responses.

    Args:
        ttl: Time-to-live in seconds. Entries older than this are considered stale.
    """

    def __init__(self, ttl: int = _DEFAULT_TTL) -> None:
        self.ttl = ttl
        self._store: dict[str, tuple[float, str]] = {}  # key -> (stored_at, value)

    def _key(self, question: str, repo: str) -> str:
        normalised = question.strip().lower()
        raw = f"{repo}:{normalised}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, question: str, repo: str) -> str | None:
        """Return cached answer, or None if absent or expired."""
        key = self._key(question, repo)
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.time() - stored_at > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, question: str, repo: str, answer: str) -> None:
        """Store an answer. Overwrites any existing entry for the same key."""
        key = self._key(question, repo)
        self._store[key] = (time.time(), answer)


# Module-level singleton used by supervisor.route()
_cache = ResponseCache()
