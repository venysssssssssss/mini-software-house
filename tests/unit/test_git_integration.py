"""Tests for git integration module."""

from unittest.mock import MagicMock, patch

from src.utils.git_integration import init_and_commit, push_to_remote


class TestInitAndCommit:
    @patch("src.utils.git_integration.subprocess.run")
    def test_success(self, mock_run, tmp_path):
        # Make all subprocess.run calls succeed
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456\n",
            stderr="",
        )

        result = init_and_commit(str(tmp_path), "test-project")

        assert result["success"] is True
        assert result["commit_hash"] == "abc123def456"
        assert result["error"] is None

        # Verify git commands called in order
        calls = mock_run.call_args_list
        assert len(calls) == 4
        assert calls[0][0][0] == ["git", "init"]
        assert calls[1][0][0] == ["git", "add", "."]
        assert calls[2][0][0] == ["git", "commit", "-m", "Initial commit: test-project"]
        assert calls[3][0][0] == ["git", "rev-parse", "HEAD"]

        # All called with cwd=workspace
        for call in calls:
            assert call[1]["cwd"] == str(tmp_path)

    @patch("src.utils.git_integration.subprocess.run")
    def test_git_init_fails(self, mock_run, tmp_path):
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "git init", stderr="fatal: error")

        result = init_and_commit(str(tmp_path), "test-project")

        assert result["success"] is False
        assert result["commit_hash"] is None
        assert "fatal: error" in result["error"]

    @patch("src.utils.git_integration.subprocess.run")
    def test_git_not_found(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError()

        result = init_and_commit(str(tmp_path), "test-project")

        assert result["success"] is False
        assert "git not found" in result["error"]


class TestPushToRemote:
    @patch("src.utils.git_integration.subprocess.run")
    def test_push_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = push_to_remote(str(tmp_path), "https://github.com/user/repo.git")

        assert result["success"] is True
        calls = mock_run.call_args_list
        assert len(calls) == 2
        assert "remote" in calls[0][0][0]
        assert "push" in calls[1][0][0]

    @patch("src.utils.git_integration.subprocess.run")
    def test_push_failure(self, mock_run, tmp_path):
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "git push", stderr="permission denied")

        result = push_to_remote(str(tmp_path), "https://github.com/user/repo.git")

        assert result["success"] is False
        assert "permission denied" in result["error"]
