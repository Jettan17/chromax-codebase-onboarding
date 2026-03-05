"""Phase 1A — Test get_readme tool against a real public repo."""

from chromax.tools.github import get_readme


def test_get_readme_returns_nonempty_string():
    result = get_readme("langchain-ai/langchain")
    assert isinstance(result, str)
    assert len(result) > 0, "README should not be empty"


def test_get_readme_contains_readme_content():
    result = get_readme("langchain-ai/langchain")
    assert not result.startswith("Error:"), f"Unexpected error: {result}"
    # README should mention the project or contain recognizable markdown
    assert any(kw in result.lower() for kw in ["langchain", "#", "install", "python"])


def test_get_readme_unknown_repo():
    result = get_readme("this-owner-does-not-exist-xyz/no-such-repo-abc123")
    assert result.startswith("Error:")
    assert "not found" in result.lower() or "access denied" in result.lower()
