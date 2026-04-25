"""Tests for generate_changelog hook."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pre_commit_hooks.generate_changelog import main


class TestGenerateChangelog:
    def test_success(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("pre_commit_hooks.generate_changelog.subprocess.run", return_value=mock_result) as mock_run:
            ret = main([])
        assert ret == 0
        mock_run.assert_called_once_with(
            ["git", "cliff", "--output", "CHANGELOG.md"],
            capture_output=True,
            text=True,
        )

    def test_custom_output(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("pre_commit_hooks.generate_changelog.subprocess.run", return_value=mock_result) as mock_run:
            ret = main(["--output", "docs/CHANGELOG.md"])
        assert ret == 0
        mock_run.assert_called_once_with(
            ["git", "cliff", "--output", "docs/CHANGELOG.md"],
            capture_output=True,
            text=True,
        )

    def test_with_tag(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("pre_commit_hooks.generate_changelog.subprocess.run", return_value=mock_result) as mock_run:
            ret = main(["--tag", "v1.2.3"])
        assert ret == 0
        mock_run.assert_called_once_with(
            ["git", "cliff", "--output", "CHANGELOG.md", "--tag", "v1.2.3"],
            capture_output=True,
            text=True,
        )

    def test_unreleased_flag(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("pre_commit_hooks.generate_changelog.subprocess.run", return_value=mock_result) as mock_run:
            ret = main(["--unreleased"])
        assert ret == 0
        mock_run.assert_called_once_with(
            ["git", "cliff", "--output", "CHANGELOG.md", "--unreleased"],
            capture_output=True,
            text=True,
        )

    def test_git_cliff_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: git-cliff failed\n"
        with patch("pre_commit_hooks.generate_changelog.subprocess.run", return_value=mock_result):
            ret = main([])
        assert ret == 1
        captured = capsys.readouterr()
        assert "error: git-cliff failed" in captured.err
