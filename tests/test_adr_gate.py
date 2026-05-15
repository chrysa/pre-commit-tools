"""Tests for adr_gate."""

from __future__ import annotations

import typing

import pytest

from pre_commit_hooks.adr_gate import check_adr_gate, matches_any_pattern


class TestMatchesAnyPattern:
    def test_exact_filename_match(self) -> None:
        assert matches_any_pattern('pyproject.toml', ['pyproject.toml']) is True

    def test_basename_match_on_nested_path(self) -> None:
        assert matches_any_pattern('subdir/pyproject.toml', ['pyproject.toml']) is True

    def test_glob_double_star_match(self) -> None:
        assert matches_any_pattern('api/routers/billing.py', ['**/routers/*.py']) is True

    def test_glob_nested_services(self) -> None:
        assert matches_any_pattern('app/services/auth.py', ['**/services/*.py']) is True

    def test_no_match(self) -> None:
        assert matches_any_pattern('README.md', ['pyproject.toml', '**/routers/*.py']) is False

    def test_dockerfile_match(self) -> None:
        assert matches_any_pattern('Dockerfile', ['Dockerfile']) is True

    def test_workflow_glob(self) -> None:
        assert matches_any_pattern('.github/workflows/ci.yml', ['**/workflows/*.yml']) is True

    def test_migration_glob(self) -> None:
        assert (
            matches_any_pattern(
                'app/migrations/versions/0001_init.py',
                ['**/migrations/versions/*.py'],
            )
            is True
        )

    def test_empty_patterns(self) -> None:
        assert matches_any_pattern('pyproject.toml', []) is False


class TestCheckAdrGate:
    _PATTERNS: typing.ClassVar[list[str]] = [
        'pyproject.toml',
        '**/routers/*.py',
        '**/services/*.py',
    ]

    def test_no_added_files_returns_0(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['README.md'],
                added_files=[],
                trigger_patterns=self._PATTERNS,
            )
            == 0
        )

    def test_trigger_added_without_decisions_returns_1(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['api/routers/billing.py'],
                added_files=['api/routers/billing.py'],
                trigger_patterns=self._PATTERNS,
            )
            == 1
        )

    def test_trigger_added_with_decisions_returns_0(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['api/routers/billing.py', 'DECISIONS.md'],
                added_files=['api/routers/billing.py'],
                trigger_patterns=self._PATTERNS,
            )
            == 0
        )

    def test_non_trigger_added_returns_0(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['README.md'],
                added_files=['README.md'],
                trigger_patterns=self._PATTERNS,
            )
            == 0
        )

    def test_warn_only_returns_0_on_violation(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['api/routers/billing.py'],
                added_files=['api/routers/billing.py'],
                trigger_patterns=self._PATTERNS,
                warn_only=True,
            )
            == 0
        )

    def test_custom_decisions_file_not_staged(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['pyproject.toml'],
                added_files=['pyproject.toml'],
                trigger_patterns=self._PATTERNS,
                decisions_file='ADR.md',
            )
            == 1
        )

    def test_custom_decisions_file_staged(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['pyproject.toml', 'ADR.md'],
                added_files=['pyproject.toml'],
                trigger_patterns=self._PATTERNS,
                decisions_file='ADR.md',
            )
            == 0
        )

    def test_modified_trigger_file_does_not_block(self) -> None:
        """Modifying a trigger file (not adding) does not trigger the gate."""
        assert (
            check_adr_gate(
                staged_files=['pyproject.toml'],
                added_files=[],  # not in added_files -> modification only
                trigger_patterns=self._PATTERNS,
            )
            == 0
        )

    def test_multiple_triggered_files_all_listed(self, capsys: pytest.CaptureFixture[str]) -> None:
        check_adr_gate(
            staged_files=['api/routers/billing.py', 'api/services/billing.py'],
            added_files=['api/routers/billing.py', 'api/services/billing.py'],
            trigger_patterns=self._PATTERNS,
        )
        out = capsys.readouterr().out
        assert 'api/routers/billing.py' in out
        assert 'api/services/billing.py' in out

    def test_output_mentions_decisions_file(self, capsys: pytest.CaptureFixture[str]) -> None:
        check_adr_gate(
            staged_files=['pyproject.toml'],
            added_files=['pyproject.toml'],
            trigger_patterns=self._PATTERNS,
        )
        out = capsys.readouterr().out
        assert 'DECISIONS.md' in out
        assert 'git add DECISIONS.md' in out

    def test_empty_trigger_patterns_returns_0(self) -> None:
        assert (
            check_adr_gate(
                staged_files=['pyproject.toml'],
                added_files=['pyproject.toml'],
                trigger_patterns=[],
            )
            == 0
        )
