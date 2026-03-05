"""Session-based conversation memory stored as JSON on disk."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SESSIONS_DIR = Path.home() / ".chromax" / "sessions"

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def _validate_session_id(session_id: str) -> None:
    """Reject session IDs that could cause path traversal."""
    if not _SESSION_ID_RE.match(session_id):
        raise ValueError(
            f"Invalid session_id {session_id!r}: only alphanumeric, hyphens, "
            "and underscores are allowed (1-128 chars)."
        )


def load_session(session_id: str) -> list[dict[str, Any]]:
    """Load message history for a session.

    Returns a list of ``{"role": "human"|"ai", "content": str}`` dicts,
    or an empty list if the session does not exist.
    """
    _validate_session_id(session_id)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return []


def save_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Persist message history for a session."""
    _validate_session_id(session_id)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSIONS_DIR / f"{session_id}.json"
    session_file.write_text(json.dumps(messages, indent=2), encoding="utf-8")


def clear_session(session_id: str) -> None:
    """Delete a session's message history from disk."""
    _validate_session_id(session_id)
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
