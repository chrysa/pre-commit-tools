"""Tests for unreachable_code_detection."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pre_commit_hooks.unreachable_code_detection import _check_body, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


def _parse_body(src: str) -> list[ast.stmt]:
    """Return the body of the first function defined in src."""
    tree = ast.parse(src)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    return func.body


class TestCheckBody:
    def test_no_terminal_returns_empty(self) -> None:
        body = _parse_body('def f():\n    x = 1\n    y = 2\n')
        assert _check_body(body, 'f.py', []) == []

    def test_return_at_end_returns_empty(self) -> None:
        body = _parse_body('def f():\n    x = 1\n    return x\n')
        assert _check_body(body, 'f.py', []) == []

    def test_return_before_stmt_returns_violation(self) -> None:
        body = _parse_body('def f():\n    return 1\n    x = 2\n')
        violations = _check_body(body, 'test.py', [])
        assert len(violations) == 1
        filename, _lineno, msg = violations[0]
        assert filename == 'test.py'
        assert 'unreachable' in msg
        assert 'return' in msg

    def test_raise_before_stmt_returns_violation(self) -> None:
        body = _parse_body('def f():\n    raise ValueError()\n    x = 1\n')
        violations = _check_body(body, 'test.py', [])
        assert len(violations) == 1

    def test_disable_comment_suppresses_violation(self) -> None:
        body = _parse_body('def f():\n    return 1\n    x = 2\n')
        # Unreachable line is source line index 2 (0-based)
        source_lines = ['def f():', '    return 1', '    x = 2  # unreachable-code: disable']
        assert _check_body(body, 'test.py', source_lines) == []


class TestUnreachableCodeMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'def f():\n    x = 1\n    return x\n')
        assert main([f]) == 0

    def test_unreachable_after_return_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'def f():\n    return 1\n    x = 2\n')
        assert main([f]) == 1

    def test_unreachable_after_raise_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'def f():\n    raise ValueError()\n    x = 1\n')
        assert main([f]) == 1

    def test_unreachable_after_break_in_loop_returns_1(self, tmp_path: Path) -> None:
        code = 'def f():\n    for i in range(10):\n        break\n        x = 1\n'
        f = _write(tmp_path, 'loop.py', code)
        assert main([f]) == 1

    def test_unreachable_after_continue_in_loop_returns_1(self, tmp_path: Path) -> None:
        code = 'def f():\n    for i in range(10):\n        continue\n        x = 1\n'
        f = _write(tmp_path, 'loop.py', code)
        assert main([f]) == 1

    def test_syntax_error_skipped_gracefully(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'err.py', 'def f(:\n    pass\n')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0

    def test_if_block_unreachable(self, tmp_path: Path) -> None:
        code = 'def f(x):\n    if x:\n        return 1\n        dead = True\n    return 0\n'
        f = _write(tmp_path, 'if_dead.py', code)
        assert main([f]) == 1

    @pytest.mark.parametrize('py_version', ['3.13', '3.14'])
    def test_try_block_unreachable(self, tmp_path: Path, py_version: str) -> None:
        """Ensure try-block analysis doesn't crash on supported Python versions."""
        code = 'def f():\n    try:\n        raise ValueError()\n        x = 1\n    except ValueError:\n        pass\n'
        f = _write(tmp_path, 'try_dead.py', code)
        assert main([f]) == 1
