"""Session-based conversation memory stored as JSON on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SESSIONS_DIR = Path.home() / ".chromax" / "sessions"


def load_session(session_id: str) -> list[dict[str, Any]]:
    """Load message history for a session.

    Returns a list of ``{"role": "human"|"ai", "content": str}`` dicts,
    or an empty list if the session does not exist.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return []


def save_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Persist message history for a session."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSIONS_DIR / f"{session_id}.json"
    session_file.write_text(json.dumps(messages, indent=2), encoding="utf-8")


def clear_session(session_id: str) -> None:
    """Delete a session's message history from disk."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
