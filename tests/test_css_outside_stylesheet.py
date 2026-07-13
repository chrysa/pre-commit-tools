"""Tests for css_outside_stylesheet."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.css_outside_stylesheet import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


@pytest.mark.parametrize(
    'stmt',
    [
        'const Btn = styled.button`\n',
        'const Box = styled(Card)`\n',
        'const g = createGlobalStyle`\n',
        'const spin = keyframes`\n',
        'const cls = css`\n',
        'injectGlobal`\n',
        '  return <div><style>{globalCss}</style></div>;\n',
        '<style type="text/css">\n',
    ],
)
class TestCssOutsideStylesheetDetection:
    def test_css_in_js_returns_1(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'bad.tsx', stmt)
        assert main([f]) == 1

    def test_disable_comment_suppresses(self, tmp_path: Path, stmt: str) -> None:
        line = stmt.rstrip('\n') + '  // css-outside-stylesheet: disable\n'
        f = _write(tmp_path, 'ok.tsx', line)
        assert main([f]) == 0

    def test_commented_line_suppressed(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'ok.tsx', '// ' + stmt)
        assert main([f]) == 0


class TestCssOutsideStylesheetClean:
    def test_classname_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', '<div className="container">\n')
        assert main([f]) == 0

    def test_styled_import_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', "import styled from 'styled-components';\n")
        assert main([f]) == 0

    def test_css_identifier_call_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', 'const x = css(theme);\n')
        assert main([f]) == 0

    def test_empty_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.tsx', '')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
