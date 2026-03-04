"""GitHub API tools for Chromax."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from github import Auth, Github, GithubException, UnknownObjectException, RateLimitExceededException

load_dotenv()

_client_cache: dict[str, Github] = {}


def _get_client() -> Github:
    token = os.getenv("GITHUB_TOKEN") or ""
    if token not in _client_cache:
        _client_cache[token] = Github(auth=Auth.Token(token)) if token else Github()
    return _client_cache[token]


def get_readme(repo: str) -> str:
    """Fetch the README content for a GitHub repository.

    Args:
        repo: Repository in 'owner/name' format (e.g. 'langchain-ai/langchain').

    Returns:
        README text, or an error message string.
    """
    try:
        g = _get_client()
        r = g.get_repo(repo)
        readme = r.get_readme()
        return readme.decoded_content.decode("utf-8", errors="replace")
    except RateLimitExceededException:
        return f"Error: GitHub API rate limit exceeded. Set GITHUB_TOKEN to increase limits."
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
    except RateLimitExceededException:
        return "Error: GitHub API rate limit exceeded."
    except UnknownObjectException:
        return f"Error: Repository '{repo}' not found."
    except GithubException as exc:
        if exc.status == 403:
            return f"Error: Access denied to '{repo}'. Check your GITHUB_TOKEN permissions."
        return f"Error: GitHub API error {exc.status}: {exc.data.get('message', str(exc))}"


def get_file_content(repo: str, path: str) -> str:
    """Fetch the raw content of a specific file in a repository.

    Args:
        repo: Repository in 'owner/name' format.
        path: File path within the repo (e.g. 'src/auth.py').

    Returns:
        File content as a string, or an error message.
    """
    MAX_BYTES = 100_000  # 100 KB limit

    try:
        g = _get_client()
        r = g.get_repo(repo)
        content_file = r.get_contents(path)

        # get_contents can return a list for directories
        if isinstance(content_file, list):
            return f"Error: '{path}' is a directory, not a file."

        if content_file.size > MAX_BYTES:
            return (
                f"Error: File '{path}' is {content_file.size:,} bytes "
                f"(limit {MAX_BYTES:,} bytes). File skipped."
            )

        return content_file.decoded_content.decode("utf-8", errors="replace")
    except RateLimitExceededException:
        return "Error: GitHub API rate limit exceeded."
    except UnknownObjectException:
        return f"Error: File '{path}' not found in '{repo}'."
    except GithubException as exc:
        if exc.status == 403:
            return f"Error: Access denied to '{repo}'. Check your GITHUB_TOKEN permissions."
        return f"Error: GitHub API error {exc.status}: {exc.data.get('message', str(exc))}"
