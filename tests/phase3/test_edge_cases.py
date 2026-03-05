"""Phase 3C — Test error handling and edge cases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from chromax.indexer.chunker import is_text_file
from chromax.tools.github import get_file_content, get_readme

# ---------- File size / type edge cases (no network needed) ----------

class TestFileSizeEdgeCases:
    def test_500kb_file_is_rejected(self):
        assert is_text_file("large.py", 500_000) is False

    def test_exactly_100kb_is_accepted(self):
        assert is_text_file("ok.py", 100_000) is True

    def test_just_over_100kb_is_rejected(self):
        assert is_text_file("big.py", 100_001) is False

    def test_env_file_not_indexed(self):
        """Ensure .env files are never indexed (security — secret leakage)."""
        assert is_text_file(".env", 100) is False
        assert is_text_file("config/.env", 100) is False

    def test_binary_extensions_rejected(self):
        for ext in ["image.png", "photo.jpg", "archive.zip", "binary.exe"]:
            assert is_text_file(ext, 100) is False, f"{ext} should be rejected"


# ---------- GitHub tool error handling ----------

class TestGitHubErrorHandling:
    def test_rate_limit_triggers_retry_and_succeeds(self):
        """get_readme retries on RateLimitExceededException and returns content on success."""
        from github import RateLimitExceededException

        call_count = 0

        def readme_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate rate limit structure expected by PyGitHub
                raise RateLimitExceededException(403, {"message": "rate limit"}, {})
            mock_readme = MagicMock()
            mock_readme.decoded_content = b"# README content"
            return mock_readme

        with patch("chromax.tools.github._get_client") as mock_get_client, \
             patch("chromax.tools.github.time") as mock_time:
            mock_github = MagicMock()
            mock_repo = MagicMock()
            mock_get_client.return_value = mock_github
            mock_github.get_repo.return_value = mock_repo
            mock_repo.get_readme.side_effect = readme_side_effect

            result = get_readme("test/repo")

        assert call_count == 2, "Should have retried once"
        mock_time.sleep.assert_called_once_with(1)
        assert "README" in result

    def test_rate_limit_exhausted_returns_error_string(self):
        """After all retries, get_readme returns a graceful error string."""
        from github import RateLimitExceededException

        with patch("chromax.tools.github._get_client") as mock_get_client, \
             patch("chromax.tools.github.time"):
            mock_github = MagicMock()
            mock_repo = MagicMock()
            mock_get_client.return_value = mock_github
            mock_github.get_repo.return_value = mock_repo
            mock_repo.get_readme.side_effect = RateLimitExceededException(
                403, {"message": "rate limit"}, {}
            )

            result = get_readme("test/repo")

        assert result.startswith("Error:"), f"Expected error string, got: {result[:100]}"

    def test_private_repo_returns_access_denied(self):
        """Accessing a private repo without access returns a clear error."""
        from github import GithubException

        with patch("chromax.tools.github._get_client") as mock_get_client:
            mock_github = MagicMock()
            mock_github.get_repo.side_effect = GithubException(
                403, {"message": "Repository access blocked"}, {}
            )
            mock_get_client.return_value = mock_github

            result = get_readme("private/repo")

        assert "Error:" in result
        assert "403" in result or "Access denied" in result or "access" in result.lower()

    def test_missing_file_returns_error(self):
        from github import UnknownObjectException

        with patch("chromax.tools.github._get_client") as mock_get_client:
            mock_github = MagicMock()
            mock_repo = MagicMock()
            mock_get_client.return_value = mock_github
            mock_github.get_repo.return_value = mock_repo
            mock_repo.get_contents.side_effect = UnknownObjectException(
                404, {"message": "Not Found"}, {}
            )

            result = get_file_content("test/repo", "nonexistent.py")

        assert result.startswith("Error:")
