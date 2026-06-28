"""Tests for file_too_long."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.file_too_long import main


def _py(tmp_path: Path, lines: int) -> str:
    p = tmp_path / 'm.py'
    p.write_text('x = 1\n' * lines, encoding='utf-8')
    return str(p)


class TestFileTooLong:
    def test_over_threshold_flagged(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '10', _py(tmp_path, 11)]) == 1

    def test_at_threshold_ok(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '10', _py(tmp_path, 10)]) == 0

    def test_default_500_ok_for_small_file(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 50)]) == 0
