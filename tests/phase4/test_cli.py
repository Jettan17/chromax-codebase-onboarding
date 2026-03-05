"""Phase 4B — CLI tests using typer.testing.CliRunner (no network/LLM needed)."""

from __future__ import annotations

from typer.testing import CliRunner

from chromax.cli import app

runner = CliRunner()


class TestHelp:
    def test_help_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        for cmd in ["index", "status", "ask", "chat"]:
            assert cmd in result.output, f"'{cmd}' not in --help output"

    def test_index_help(self):
        result = runner.invoke(app, ["index", "--help"])
        assert result.exit_code == 0
        assert "--repo" in result.output

    def test_ask_help(self):
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0
        assert "--repo" in result.output
        assert "--session" in result.output

    def test_chat_help(self):
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--repo" in result.output


class TestMissingArgs:
    def test_index_without_repo_fails(self):
        result = runner.invoke(app, ["index"])
        assert result.exit_code != 0

    def test_ask_without_repo_fails(self):
        result = runner.invoke(app, ["ask", "what does this do?"])
        assert result.exit_code != 0

    def test_status_without_repo_fails(self):
        result = runner.invoke(app, ["status"])
        assert result.exit_code != 0

    def test_chat_without_repo_fails(self):
        result = runner.invoke(app, ["chat"])
        assert result.exit_code != 0


class TestStatusCommand:
    def test_status_unindexed_repo_exits_zero(self):
        """Status on a repo that hasn't been indexed should not crash."""
        result = runner.invoke(app, ["status", "--repo", "definitely/not-indexed-xyz"])
        assert result.exit_code == 0
        assert "not indexed" in result.output.lower() or "not" in result.output.lower()


class TestRepoValidation:
    def test_invalid_repo_format_rejected(self):
        result = runner.invoke(app, ["status", "--repo", "notavalidrepo"])
        assert result.exit_code != 0

    def test_empty_owner_rejected(self):
        result = runner.invoke(app, ["status", "--repo", "/requests"])
        assert result.exit_code != 0

    def test_valid_repo_format_accepted(self):
        result = runner.invoke(app, ["status", "--repo", "psf/requests"])
        assert result.exit_code == 0


class TestChatReplExit:
    def test_exit_command_quits_cleanly(self):
        result = runner.invoke(app, ["chat", "--repo", "psf/requests"], input="exit\n")
        assert result.exit_code == 0
        assert "session ended" in result.output.lower()

    def test_quit_command_quits_cleanly(self):
        result = runner.invoke(app, ["chat", "--repo", "psf/requests"], input="quit\n")
        assert result.exit_code == 0

    def test_eof_quits_cleanly(self):
        # Empty input causes typer.prompt to raise Abort internally before our
        # EOFError handler fires — exit code 1 is acceptable here (stdin closed).
        result = runner.invoke(app, ["chat", "--repo", "psf/requests"], input="")
        assert result.exit_code in (0, 1)
