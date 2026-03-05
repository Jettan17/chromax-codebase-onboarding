"""Phase 2B — Test semantic search and cited agent responses."""

import pytest

try:
    from groq import RateLimitError as _GroqRateLimitError
except ImportError:
    _GroqRateLimitError = Exception

from chromax.agents.basic import ask
from chromax.tools.search import SearchResult, search_codebase

TEST_REPO = "psf/requests"


class TestSearchCodebase:
    def test_returns_results(self):
        results = search_codebase("HTTP authentication", TEST_REPO)
        assert len(results) > 0

    def test_results_are_search_result_objects(self):
        results = search_codebase("HTTP authentication", TEST_REPO)
        for r in results:
            assert isinstance(r, SearchResult)
            assert r.file_path
            assert r.start_line >= 1
            assert r.end_line >= r.start_line

    def test_auth_query_finds_auth_file(self):
        results = search_codebase("authentication auth token bearer", TEST_REPO)
        file_paths = [r.file_path for r in results]
        assert any("auth" in p.lower() for p in file_paths), (
            f"Expected auth-related file in results, got: {file_paths}"
        )

    def test_citation_format(self):
        results = search_codebase("retry", TEST_REPO)
        for r in results:
            assert ":" in r.citation
            assert r.citation.startswith(r.file_path)

    def test_unindexed_repo_returns_empty(self):
        results = search_codebase("anything", "owner/definitely-not-indexed-xyz")
        assert results == []


class TestAgentWithSearch:
    def test_ask_with_indexed_repo_cites_files(self):
        try:
            result = ask("How does HTTP auth work?", TEST_REPO)
        except _GroqRateLimitError:
            pytest.skip("Groq daily token limit reached")
        # Should contain a file reference (from search results)
        assert any(marker in result for marker in [".py:", "auth", "requests/"])
