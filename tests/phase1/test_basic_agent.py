"""Phase 1C — Test the basic LangGraph agent (single API call to respect free tier)."""

import pytest
from chromax.agents.basic import ask

TEST_REPO = "langchain-ai/langchain"


def test_ask_about_repo():
    """One call, three assertions — avoids hammering the free-tier quota."""
    result = ask("What does this repo do?", TEST_REPO)

    assert isinstance(result, str), "Result should be a string"
    assert len(result) > 50, "Answer should be substantial"

    result_lower = result.lower()
    assert any(kw in result_lower for kw in ["langchain", "llm", "language model", "ai", "chain"]), (
        f"Answer should mention the repo topic. Got: {result[:200]}"
    )

    # Grounded response: should reference at least one file, path, or markdown element
    assert any(marker in result for marker in ["README", ".md", ".py", "src/", "/", "`"]), (
        f"Answer should cite at least one file reference. Got: {result[:200]}"
    )
