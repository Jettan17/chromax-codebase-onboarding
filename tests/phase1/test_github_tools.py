"""Phase 1B — Tests for get_repo_structure and get_file_content."""

from chromax.tools.github import get_file_content, get_repo_structure

TEST_REPO = "psf/requests"


class TestGetRepoStructure:
    def test_returns_nonempty_tree(self):
        result = get_repo_structure(TEST_REPO)
        assert isinstance(result, str)
        assert len(result) > 0
        assert not result.startswith("Error:")

    def test_tree_starts_with_repo_name(self):
        result = get_repo_structure(TEST_REPO)
        assert result.startswith(TEST_REPO + "/")

    def test_tree_contains_known_files(self):
        result = get_repo_structure(TEST_REPO)
        # psf/requests always has these
        assert "requests" in result
        assert "README" in result or "readme" in result.lower()

    def test_unknown_repo_returns_error(self):
        result = get_repo_structure("this-owner-xyz/no-such-repo-abc")
        assert result.startswith("Error:")
        assert "not found" in result.lower() or "access denied" in result.lower()


class TestGetFileContent:
    def test_returns_file_content(self):
        result = get_file_content(TEST_REPO, "README.md")
        assert isinstance(result, str)
        assert len(result) > 0
        assert not result.startswith("Error:")

    def test_content_contains_expected_text(self):
        result = get_file_content(TEST_REPO, "README.md")
        assert "requests" in result.lower()

    def test_missing_file_returns_error(self):
        result = get_file_content(TEST_REPO, "no_such_file_xyz.py")
        assert result.startswith("Error:")
        assert "not found" in result.lower()

    def test_unknown_repo_returns_error(self):
        result = get_file_content("this-owner-xyz/no-such-repo-abc", "README.md")
        assert result.startswith("Error:")
