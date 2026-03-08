"""Phase 5 — CliRunner tests for the `chromax arch` command (no network/LLM needed)."""

from __future__ import annotations

from typer.testing import CliRunner

from chromax.cli import app

runner = CliRunner()


class TestArchHelp:
    def test_top_level_help_lists_arch(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "arch" in result.output

    def test_arch_help_exits_zero(self):
        result = runner.invoke(app, ["arch", "--help"])
        assert result.exit_code == 0

    def test_arch_help_shows_repo_option(self):
        result = runner.invoke(app, ["arch", "--help"])
        assert "--repo" in result.output

    def test_arch_help_shows_session_option(self):
        result = runner.invoke(app, ["arch", "--help"])
        assert "--session" in result.output


class TestArchArgValidation:
    def test_arch_without_repo_fails(self):
        result = runner.invoke(app, ["arch"])
        assert result.exit_code != 0

    def test_arch_with_question_but_no_repo_fails(self):
        result = runner.invoke(app, ["arch", "what is the architecture?"])
        assert result.exit_code != 0

    def test_arch_invalid_repo_format_fails(self):
        result = runner.invoke(app, ["arch", "--repo", "notaslash"])
        assert result.exit_code != 0

    def test_arch_invalid_repo_empty_owner_fails(self):
        result = runner.invoke(app, ["arch", "--repo", "/myrepo"])
        assert result.exit_code != 0
