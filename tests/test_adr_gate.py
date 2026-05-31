"""Tests for adr_gate."""

from __future__ import annotations

import typing

import pytest

from pre_commit_hooks.adr_gate import check_adr_gate, get_all_staged_files, matches_any_pattern


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

    def test_decisions_in_all_staged_but_not_in_argv_returns_0(self) -> None:
        """Regression test for #176: DECISIONS.md staged but absent from pre-commit argv.

        This happens when ruff-format (or another hook) runs before adr-gate and
        modifies the working tree, causing pre-commit to rebuild the staged-file list
        without including DECISIONS.md in argv even though it is staged.
        """
        assert (
            check_adr_gate(
                staged_files=['api/routers/billing.py'],  # DECISIONS.md absent from argv
                added_files=['api/routers/billing.py'],
                trigger_patterns=self._PATTERNS,
                all_staged_files=['api/routers/billing.py', 'DECISIONS.md'],  # present in git index
            )
            == 0
        )

    def test_decisions_absent_from_both_argv_and_git_index_returns_1(self) -> None:
        """When DECISIONS.md is absent from both pre-commit argv and git index, return 1."""
        assert (
            check_adr_gate(
                staged_files=['api/routers/billing.py'],
                added_files=['api/routers/billing.py'],
                trigger_patterns=self._PATTERNS,
                all_staged_files=['api/routers/billing.py'],  # DECISIONS.md still absent
            )
            == 1
        )

    def test_all_staged_files_none_falls_back_to_staged_files_with_decisions(self) -> None:
        """When all_staged_files is None, only staged_files (argv) is checked (backward compat)."""
        assert (
            check_adr_gate(
                staged_files=['api/routers/billing.py', 'DECISIONS.md'],
                added_files=['api/routers/billing.py'],
                trigger_patterns=self._PATTERNS,
                all_staged_files=None,
            )
            == 0
        )


class TestGetAllStagedFiles:
    def test_returns_list(self, tmp_path: pytest.TempPathFactory) -> None:
        """get_all_staged_files() always returns a list (even outside a git repo)."""
        result = get_all_staged_files()
        assert isinstance(result, list)


class TestMain:
    """Tests for main() — argparse wiring and subprocess delegation."""

    def _run(self, argv: list[str], added: list[str], all_staged: list[str]) -> int:
        from unittest.mock import patch

        from pre_commit_hooks.adr_gate import main

        with (
            patch('pre_commit_hooks.adr_gate.get_added_files', return_value=added),
            patch('pre_commit_hooks.adr_gate.get_all_staged_files', return_value=all_staged),
        ):
            return main(argv)

    def test_no_trigger_returns_0(self) -> None:
        """main() returns 0 when no architecture-sensitive files are added."""
        qg = self._run(['some_file.txt'], added=['some_file.txt'], all_staged=['some_file.txt'])
        assert qg == 0

    def test_trigger_without_decisions_returns_1(self) -> None:
        """main() returns 1 when a trigger file is added without DECISIONS.md."""
        qg = self._run(
            ['pyproject.toml'],
            added=['pyproject.toml'],
            all_staged=['pyproject.toml'],
        )
        assert qg == 1

    def test_trigger_with_decisions_returns_0(self) -> None:
        """main() returns 0 when a trigger file is added with DECISIONS.md staged."""
        qg = self._run(
            ['pyproject.toml', 'DECISIONS.md'],
            added=['pyproject.toml'],
            all_staged=['pyproject.toml', 'DECISIONS.md'],
        )
        assert qg == 0

    def test_warn_only_flag_returns_0(self) -> None:
        """main() with --warn-only returns 0 even if DECISIONS.md is missing."""
        qg = self._run(
            ['pyproject.toml', '--warn-only'],
            added=['pyproject.toml'],
            all_staged=['pyproject.toml'],
        )
        assert qg == 0

    def test_custom_decisions_file(self) -> None:
        """main() respects --decisions-file argument."""
        qg = self._run(
            ['pyproject.toml', '--decisions-file', 'CHANGELOG.md'],
            added=['pyproject.toml'],
            all_staged=['pyproject.toml', 'CHANGELOG.md'],
        )
        assert qg == 0

    def test_custom_trigger_patterns(self) -> None:
        """main() respects --trigger-patterns argument."""
        qg = self._run(
            ['custom_arch.py', '--trigger-patterns', 'custom_arch.py'],
            added=['custom_arch.py'],
            all_staged=['custom_arch.py'],
        )
        assert qg == 1

    def test_no_filenames_returns_0(self) -> None:
        """main() with no filenames (empty argv) returns 0 — nothing staged."""
        qg = self._run([], added=[], all_staged=[])
        assert qg == 0
