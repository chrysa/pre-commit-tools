"""Tests for react_console_error_detection."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.react_console_error_detection import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestReactConsoleErrorMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.js', 'function f() {\n  return 1;\n}\n')
        assert main([f]) == 0

    def test_console_error_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.js', 'console.error("oops");\n')
        assert main([f]) == 1

    def test_console_error_in_tsx_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.tsx', 'console.error(err);\n')
        assert main([f]) == 1

    def test_commented_console_error_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.ts', '// console.error("debug");\n')
        assert main([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'ok.js',
            'console.error(err); // console-error-detection: disable\n',
        )
        assert main([f]) == 0

    def test_indented_console_error_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.js', 'function f() {\n  console.error("x");\n}\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
