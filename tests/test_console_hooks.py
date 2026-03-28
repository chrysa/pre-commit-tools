"""Tests for console_debug_detection, console_log_detection, console_table_detection."""
from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.console_debug_detection import main as debug_main
from pre_commit_hooks.console_log_detection import main as log_main
from pre_commit_hooks.console_table_detection import main as table_main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


@pytest.mark.parametrize('main_fn,stmt,disable_key', [
    (debug_main, 'console.debug("x");\n', 'console-debug-detection'),
    (log_main, 'console.log("x");\n', 'console-log-detection'),
    (table_main, 'console.table(data);\n', 'console-table-detection'),
])
class TestConsoleDetection:
    def test_statement_returns_1(
        self,
        tmp_path: Path,
        main_fn: object,
        stmt: str,
        disable_key: str,
    ) -> None:
        f = _write(tmp_path, 'bad.js', stmt)
        assert main_fn([f]) == 1  # type: ignore[operator]

    def test_clean_returns_0(
        self,
        tmp_path: Path,
        main_fn: object,
        stmt: str,
        disable_key: str,
    ) -> None:
        f = _write(tmp_path, 'ok.js', 'const x = 1;\n')
        assert main_fn([f]) == 0  # type: ignore[operator]

    def test_commented_returns_0(
        self,
        tmp_path: Path,
        main_fn: object,
        stmt: str,
        disable_key: str,
    ) -> None:
        f = _write(tmp_path, 'c.js', f'// {stmt}')
        assert main_fn([f]) == 0  # type: ignore[operator]

    def test_disable_comment_returns_0(
        self,
        tmp_path: Path,
        main_fn: object,
        stmt: str,
        disable_key: str,
    ) -> None:
        f = _write(tmp_path, 'd.js', f'{stmt.rstrip()} // {disable_key}: disable\n')
        assert main_fn([f]) == 0  # type: ignore[operator]
