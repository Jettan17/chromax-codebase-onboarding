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
