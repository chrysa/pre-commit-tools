"""Tests for function_too_long."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.function_too_long import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


def _func(n: int) -> str:
    lines = '\n'.join(f'    x{i} = {i}' for i in range(n))
    return f'def big():\n{lines}\n'


class TestFunctionTooLong:
    def test_over_threshold_flagged(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '5', _py(tmp_path, _func(10))]) == 1

    def test_under_threshold_ok(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '50', _py(tmp_path, _func(3))]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        body = 'def big():  # function-too-long: disable\n' + '\n'.join(f'    x{i} = {i}' for i in range(10)) + '\n'
        assert main(['--max-lines', '5', _py(tmp_path, body)]) == 0

    def test_syntax_error_skipped(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'def broken(:\n')]) == 0
