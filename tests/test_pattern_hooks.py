"""Tests for print_detection, pprint_detection, debugger_detection, logger_detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.debugger_detection import main as debugger_main
from pre_commit_hooks.logger_detection import main as logger_main
from pre_commit_hooks.pprint_detection import main as pprint_main
from pre_commit_hooks.print_detection import main as print_main

# ── helpers ──────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


# ── print_detection ───────────────────────────────────────────────────────────


class TestPrintDetection:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'x = 1\n')
        assert print_main([f]) == 0

    def test_print_call_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'print("hello")\n')
        assert print_main([f]) == 1

    def test_commented_print_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'commented.py', '# print("hello")\n')
        assert print_main([f]) == 0

    def test_disable_comment_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'disabled.py', 'print("x")  # print-detection: disable\n')
        assert print_main([f]) == 0

    def test_multiple_files_any_bad_returns_1(self, tmp_path: Path) -> None:
        clean = _write(tmp_path, 'clean.py', 'x = 1\n')
        bad = _write(tmp_path, 'bad.py', 'print("oops")\n')
        assert print_main([clean, bad]) == 1

    def test_empty_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'empty.py', '')
        assert print_main([f]) == 0


# ── pprint_detection ──────────────────────────────────────────────────────────


class TestPprintDetection:
    def test_clean_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'x = 1\n')
        assert pprint_main([f]) == 0

    def test_pprint_call_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'pprint({"a": 1})\n')
        assert pprint_main([f]) == 1

    def test_commented_pprint_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'c.py', '# pprint(x)\n')
        assert pprint_main([f]) == 0

    def test_disable_comment_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'd.py', 'pprint(x)  # pprint-detection: disable\n')
        assert pprint_main([f]) == 0


# ── debugger_detection ────────────────────────────────────────────────────────


class TestDebuggerDetection:
    @pytest.mark.parametrize(
        'stmt',
        [
            'breakpoint()\n',
            'pdb.set_trace()\n',
            'ipdb.set_trace()\n',
            'pudb.set_trace()\n',
        ],
    )
    def test_debugger_stmt_returns_1(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'dbg.py', stmt)
        assert debugger_main([f]) == 1

    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'x = 1\n')
        assert debugger_main([f]) == 0

    def test_commented_breakpoint_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'c.py', '# breakpoint()\n')
        assert debugger_main([f]) == 0

    def test_disable_comment_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'd.py', 'breakpoint()  # debugger-detection: disable\n')
        assert debugger_main([f]) == 0


# ── logger_detection ──────────────────────────────────────────────────────────


class TestLoggerDetection:
    @pytest.mark.parametrize('level', ['debug', 'info', 'warning', 'error', 'critical', 'exception'])
    def test_root_logging_returns_1(self, tmp_path: Path, level: str) -> None:
        f = _write(tmp_path, 'log.py', f'logging.{level}("msg")\n')
        assert logger_main([f]) == 1

    def test_named_logger_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'log.info("msg")\n')
        assert logger_main([f]) == 0

    def test_disable_comment_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'd.py', 'logging.info("x")  # logger-detection: disable\n')
        assert logger_main([f]) == 0
