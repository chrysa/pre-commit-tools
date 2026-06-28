"""Tests for no_external_tool_config."""

from __future__ import annotations

from pre_commit_hooks.no_external_tool_config import main


class TestNoExternalToolConfig:
    def test_forbidden_ruff_toml_returns_1(self) -> None:
        assert main(['ruff.toml']) == 1

    def test_forbidden_nested_mypy_ini_returns_1(self) -> None:
        assert main(['some/dir/mypy.ini']) == 1

    def test_pytest_ini_and_coveragerc_return_1(self) -> None:
        assert main(['pytest.ini']) == 1
        assert main(['.coveragerc']) == 1

    def test_allowed_pyproject_returns_0(self) -> None:
        assert main(['pyproject.toml']) == 0

    def test_no_files_returns_0(self) -> None:
        assert main([]) == 0
