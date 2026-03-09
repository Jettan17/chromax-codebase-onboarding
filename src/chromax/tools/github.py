"""GitHub API tools for Chromax."""

from __future__ import annotations

import functools
import logging
import os
import time

from dotenv import load_dotenv
from github import Auth, Github, GithubException, RateLimitExceededException, UnknownObjectException

load_dotenv()

logger = logging.getLogger(__name__)

_client_cache: dict[str, Github] = {}

_MAX_RETRIES = 4  # up to 3 retries (attempts 0–3), backoff: 1, 2, 4 s


def _get_client() -> Github:
    token = os.getenv("GITHUB_TOKEN") or ""
    if token not in _client_cache:
        _client_cache[token] = Github(auth=Auth.Token(token)) if token else Github()
    return _client_cache[token]


def _with_retry(fn):
    """Retry a GitHub API call on RateLimitExceededException with exponential backoff."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        for attempt in range(_MAX_RETRIES):
            try:
                return fn(*args, **kwargs)
            except RateLimitExceededException:
                if attempt == _MAX_RETRIES - 1:
                    raise  # exhausted retries — let caller handle
                wait = 2 ** attempt  # 1, 2, 4 seconds
                logger.warning("GitHub rate limit hit — retrying in %ds (attempt %d/%d)", wait, attempt + 1, _MAX_RETRIES - 1)
                time.sleep(wait)
    return wrapper


@_with_retry
def _get_readme_raw(repo: str) -> str:
    g = _get_client()
    r = g.get_repo(repo)
    readme = r.get_readme()
    return readme.decoded_content.decode("utf-8", errors="replace")


@_with_retry
def _get_repo_structure_raw(repo: str, max_depth: int) -> str:
    g = _get_client()
    r = g.get_repo(repo)
    tree = r.get_git_tree(r.default_branch, recursive=True)
    lines: list[str] = [f"{repo}/"]
    for element in tree.tree:
        parts = element.path.split("/")
        if len(parts) > max_depth:
            continue
        indent = "  " * (len(parts) - 1)
        name = parts[-1]
        suffix = "/" if element.type == "tree" else ""
        lines.append(f"{indent}{name}{suffix}")
    return "\n".join(lines)


@_with_retry
def _get_file_content_raw(repo: str, path: str) -> str:
    MAX_BYTES = 100_000
    g = _get_client()
    r = g.get_repo(repo)
    content_file = r.get_contents(path)
    if isinstance(content_file, list):
        return f"Error: '{path}' is a directory, not a file."
    if content_file.size > MAX_BYTES:
        return (
            f"Error: File '{path}' is {content_file.size:,} bytes "
            f"(limit {MAX_BYTES:,} bytes). File skipped."
        )
    return content_file.decoded_content.decode("utf-8", errors="replace")


def get_readme(repo: str) -> str:
    """Fetch the README content for a GitHub repository.

    Args:
        repo: Repository in 'owner/name' format (e.g. 'langchain-ai/langchain').

    Returns:
        README text, or an error message string.
    """
    try:
        return _get_readme_raw(repo)
    except RateLimitExceededException:
        return "Error: GitHub API rate limit exceeded after retries. Set GITHUB_TOKEN to increase limits."
    except UnknownObjectException:
        return f"Error: Repository '{repo}' not found or README does not exist."
    except GithubException as exc:
        if exc.status == 403:
            return f"Error: Access denied to '{repo}'. Check your GITHUB_TOKEN permissions."
        return f"Error: GitHub API error {exc.status}: {exc.data.get('message', str(exc))}"


def get_repo_structure(repo: str, max_depth: int = 3) -> str:
    """Return a file-tree representation of the repository.

    Args:
        repo: Repository in 'owner/name' format.
        max_depth: How many directory levels to show (default 3).

    Returns:
        Tree string, or an error message.
    """
    try:
        return _get_repo_structure_raw(repo, max_depth)
    except RateLimitExceededException:
        return "Error: GitHub API rate limit exceeded after retries."
    except UnknownObjectException:
        return f"Error: Repository '{repo}' not found."
    except GithubException as exc:
        if exc.status == 403:
            return f"Error: Access denied to '{repo}'. Check your GITHUB_TOKEN permissions."
        return f"Error: GitHub API error {exc.status}: {exc.data.get('message', str(exc))}"


def get_all_file_paths(repo: str) -> list[str] | None:
    """Return a flat list of all file paths (blobs only) in a repository.

    Used by the arch agent to build the known-paths set for citation verification.

    Args:
        repo: Repository in 'owner/name' format.

    Returns:
        List of relative file paths (e.g. ['src/main.py', 'README.md']), or None on error.
    """
    try:
        g = _get_client()
        r = g.get_repo(repo)
        tree = r.get_git_tree(r.default_branch, recursive=True)
        return [element.path for element in tree.tree if element.type == "blob"]
    except Exception:
        return None


def get_file_content(repo: str, path: str) -> str:
    """Fetch the raw content of a specific file in a repository.

    Args:
        repo: Repository in 'owner/name' format.
        path: File path within the repo (e.g. 'src/auth.py').

    Returns:
        File content as a string, or an error message.
    """
    try:
        return _get_file_content_raw(repo, path)
    except RateLimitExceededException:
        return "Error: GitHub API rate limit exceeded after retries."
    except UnknownObjectException:
        return f"Error: File '{path}' not found in '{repo}'."
    except GithubException as exc:
        if exc.status == 403:
            return f"Error: Access denied to '{repo}'. Check your GITHUB_TOKEN permissions."
        return f"Error: GitHub API error {exc.status}: {exc.data.get('message', str(exc))}"
