"""Phase 5 — ArchitectAgent prompt contract and supervisor routing tests."""

from __future__ import annotations

import pytest

try:
    from groq import RateLimitError as _GroqRateLimitError
except ImportError:
    _GroqRateLimitError = Exception

pytestmark = pytest.mark.filterwarnings("ignore")


class TestArchPromptContract:
    """Verify ARCH_SYSTEM_PROMPT and OVERVIEW_PROMPT satisfy their contracts."""

    def test_overview_prompt_not_empty(self):
        from chromax.agents.arch import OVERVIEW_PROMPT

        assert isinstance(OVERVIEW_PROMPT, str)
        assert len(OVERVIEW_PROMPT.strip()) > 20

    def test_arch_system_prompt_contains_injection_defence(self):
        from chromax.agents.arch import SYSTEM_PROMPT

        lowered = SYSTEM_PROMPT.lower()
        assert "untrusted" in lowered or "data only" in lowered, (
            "ARCH_SYSTEM_PROMPT must include the standard prompt-injection defence clause"
        )

    def test_arch_system_prompt_scopes_away_from_structure_agent(self):
        """Arch agent must be instructed NOT to merely list files/directories."""
        from chromax.agents.arch import SYSTEM_PROMPT

        lowered = SYSTEM_PROMPT.lower()
        assert "list" in lowered or "directory" in lowered or "structure specialist" in lowered, (
            "ARCH_SYSTEM_PROMPT should reference the boundary with the StructureAgent"
        )

    def test_ask_arch_is_callable(self):
        from chromax.agents.arch import ask

        assert callable(ask)


class TestExtractCitations:
    """Unit tests for _extract_citations — pure function, no network."""

    def test_backtick_with_line_range(self):
        from chromax.agents.arch import _extract_citations

        result = _extract_citations("See `src/foo.py:10-20` for details.")
        assert "src/foo.py" in result

    def test_backtick_without_line(self):
        from chromax.agents.arch import _extract_citations

        result = _extract_citations("Defined in `src/bar/baz.py`.")
        assert "src/bar/baz.py" in result

    def test_bare_path_with_line_number(self):
        from chromax.agents.arch import _extract_citations

        result = _extract_citations("Coupling at src/x/y.py:42 is the issue.")
        assert "src/x/y.py" in result

    def test_deduplicates_repeated_citations(self):
        from chromax.agents.arch import _extract_citations

        result = _extract_citations("`src/foo.py:1` and `src/foo.py:5` are both relevant.")
        assert result.count("src/foo.py") == 1

    def test_empty_string_returns_empty_list(self):
        from chromax.agents.arch import _extract_citations

        assert _extract_citations("") == []

    def test_plain_prose_no_citations(self):
        from chromax.agents.arch import _extract_citations

        result = _extract_citations("This is a great codebase with no file references at all.")
        assert result == []

    def test_ignores_bare_filename_without_slash(self):
        """'File "foo.py", line 10' style should NOT be extracted (no slash)."""
        from chromax.agents.arch import _extract_citations

        result = _extract_citations('File "foo.py", line 10 — this is a Python traceback.')
        assert "foo.py" not in result


class TestVerifyCitations:
    """Unit tests for _verify_citations — pure function, no network."""

    def test_hallucination_detected_appends_warning(self):
        from chromax.agents.arch import _verify_citations

        known = {"src/real.py", "src/other.py"}
        response = "See `src/fake.py:10` and `src/real.py:5`."
        result = _verify_citations(response, known)
        assert "[!]" in result
        assert "src/fake.py" in result

    def test_all_citations_real_no_warning(self):
        from chromax.agents.arch import _verify_citations

        known = {"src/real.py"}
        response = "Everything is in `src/real.py:1-10`."
        result = _verify_citations(response, known)
        assert result == response

    def test_empty_known_paths_returns_unchanged(self):
        """Graceful degradation: if we couldn't fetch file list, don't add noise."""
        from chromax.agents.arch import _verify_citations

        response = "See `src/anything.py:5`."
        result = _verify_citations(response, set())
        assert result == response

    def test_no_citations_in_response_returns_unchanged(self):
        from chromax.agents.arch import _verify_citations

        known = {"src/real.py"}
        response = "This is a plain prose response with no file citations."
        result = _verify_citations(response, known)
        assert result == response

    def test_warning_does_not_list_real_citations(self):
        from chromax.agents.arch import _verify_citations

        known = {"src/real.py"}
        response = "See `src/real.py:1` and `src/fake.py:5`."
        result = _verify_citations(response, known)
        # real file should NOT appear in the warning block
        warning_section = result[result.index("[!]"):]
        assert "src/real.py" not in warning_section


class TestSupervisorArchRouting:
    """supervisor.classify_query() recognises architecture questions."""

    def _safe_classify(self, question: str) -> str:
        from chromax.agents.supervisor import classify_query

        try:
            return classify_query(question)
        except _GroqRateLimitError:
            pytest.skip("Groq daily token limit reached")

    def test_architecture_overview_question(self):
        assert self._safe_classify("Give me an architectural overview of this codebase") == "architecture"

    def test_design_patterns_question(self):
        assert self._safe_classify("What design patterns does this codebase use?") == "architecture"

    def test_component_relationships_question(self):
        assert self._safe_classify("How do the main components interact with each other?") == "architecture"

    def test_structure_question_still_routes_correctly(self):
        """Adding 'architecture' must not break existing structure routing."""
        result = self._safe_classify("What files are in the project?")
        assert result == "structure"

    def test_analyzer_question_still_routes_correctly(self):
        """Adding 'architecture' must not break existing analyzer routing."""
        result = self._safe_classify("How does the retry logic work?")
        assert result == "analyzer"
