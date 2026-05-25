"""Tests for python_no_type_ignore."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.python_no_type_ignore import detect_bare_type_ignore, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectBareTypeIgnore:
    def test_bare_type_ignore_detected(self) -> None:
        src = 'x = some_fn()  # type: ignore\n'
        violations = detect_bare_type_ignore(src, 'file.py')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'justification' in msg

    def test_type_ignore_with_qualifier_only_detected(self) -> None:
        src = 'x = some_fn()  # type: ignore[attr-defined]\n'
        violations = detect_bare_type_ignore(src, 'file.py')
        assert len(violations) == 1

    def test_type_ignore_with_reason_ok(self) -> None:
        src = 'x = some_fn()  # type: ignore[attr-defined]  # third-party lib missing stubs\n'
        assert detect_bare_type_ignore(src, 'file.py') == []

    def test_type_ignore_with_inline_reason_ok(self) -> None:
        src = 'x = some_fn()  # type: ignore  # legacy code, cannot fix now\n'
        assert detect_bare_type_ignore(src, 'file.py') == []

    def test_disable_comment_suppresses(self) -> None:
        src = 'x = some_fn()  # type: ignore  # python-no-type-ignore: disable\n'
        assert detect_bare_type_ignore(src, 'file.py') == []

    def test_multiple_violations_found(self) -> None:
        src = 'a = foo()  # type: ignore\nb = bar()  # type: ignore[misc]\n'
        violations = detect_bare_type_ignore(src, 'file.py')
        assert len(violations) == 2

    def test_no_type_ignore_ok(self) -> None:
        src = 'x: int = 1\ny: str = "hello"\n'
        assert detect_bare_type_ignore(src, 'file.py') == []

    @pytest.mark.parametrize(
        'line',
        [
            'x = f()  # type: ignore[return-value]  # reason here\n',
            'x = f()  # type: ignore  # noqa: F401 — intentional\n',
        ],
    )
    def test_with_reason_variants_ok(self, line: str) -> None:
        assert detect_bare_type_ignore(line, 'file.py') == []


class TestPythonNoTypeIgnoreMain:
    def test_bare_ignore_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'x = f()  # type: ignore\n')
        assert main([f]) == 1

    def test_with_reason_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'x = f()  # type: ignore[misc]  # needed\n')
        assert main([f]) == 0

    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'x: int = 1\n')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
