"""Phase 3A — Test supervisor routing to specialist agents."""

import pytest

try:
    from groq import RateLimitError as _GroqRateLimitError
except ImportError:
    _GroqRateLimitError = Exception

from chromax.agents.supervisor import classify_query, route

pytestmark = pytest.mark.filterwarnings("ignore")

TEST_REPO = "psf/requests"


class TestClassifyQuery:
    """classify_query() routes queries to the right specialist category."""

    def _safe_classify(self, question: str) -> str:
        try:
            return classify_query(question)
        except _GroqRateLimitError:
            pytest.skip("Groq daily token limit reached")

    def test_structure_query(self):
        assert self._safe_classify("What files are in the project?") == "structure"

    def test_analyzer_query(self):
        assert self._safe_classify("How does the retry logic work?") == "analyzer"

    def test_navigation_query(self):
        assert self._safe_classify("Where is the auth code?") == "navigation"

    def test_search_query(self):
        assert self._safe_classify("Find code similar to async request handling") == "search"


class TestRoute:
    def test_route_returns_string(self):
        try:
            result = route("What files are in the project?", TEST_REPO)
        except _GroqRateLimitError:
            pytest.skip("Groq daily token limit reached")
        assert isinstance(result, str)
        assert len(result) > 20

    def test_route_structure_mentions_files(self):
        try:
            result = route("What files are in the project?", TEST_REPO)
        except _GroqRateLimitError:
            pytest.skip("Groq daily token limit reached")
        result_lower = result.lower()
        assert any(kw in result_lower for kw in ["requests", ".py", "file", "directory", "folder", "src"])
