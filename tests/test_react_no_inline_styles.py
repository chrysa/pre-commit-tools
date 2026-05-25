"""Tests for react_no_inline_styles."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.react_no_inline_styles import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


@pytest.mark.parametrize(
    'stmt',
    [
        '<div style={{ color: "red" }}>\n',
        'return <span style={{fontSize: 12}}/>;\n',
        '<Component style={{ margin: 0, padding: 0 }} />\n',
    ],
)
class TestReactNoInlineStylesDetection:
    def test_inline_style_returns_1(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'bad.tsx', stmt)
        assert main([f]) == 1

    def test_disable_comment_suppresses(self, tmp_path: Path, stmt: str) -> None:
        line = stmt.rstrip('\n') + '  // react-no-inline-styles: disable\n'
        f = _write(tmp_path, 'ok.tsx', line)
        assert main([f]) == 0

    def test_commented_line_suppressed(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'ok.tsx', '// ' + stmt)
        assert main([f]) == 0


class TestReactNoInlineStylesClean:
    def test_classname_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', '<div className="container">\n')
        assert main([f]) == 0

    def test_style_variable_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', '<div style={containerStyles}>\n')
        assert main([f]) == 0

    def test_empty_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', '')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
