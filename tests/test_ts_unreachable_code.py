"""Tests for ts_unreachable_code_detection."""

from __future__ import annotations

from pathlib import Path

import pytest

tree_sitter = pytest.importorskip('tree_sitter', reason='tree-sitter not installed')
tree_sitter_typescript = pytest.importorskip('tree_sitter_typescript', reason='tree-sitter-typescript not installed')

from pre_commit_hooks.ts_unreachable_code_detection import _walk, main  # noqa: E402


def _make_ts_tree(source: str) -> object:
    import tree_sitter_typescript as tsts
    from tree_sitter import Language, Parser

    lang = Language(tsts.language_typescript())
    parser = Parser(lang)
    return parser.parse(source.encode())


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestWalk:
    def test_no_unreachable_returns_empty(self) -> None:
        src = 'function f() { const x = 1; return x; }'
        tree = _make_ts_tree(src)
        assert _walk(tree.root_node, 'f.ts', src.splitlines()) == []

    def test_return_before_stmt_is_violation(self) -> None:
        src = 'function f() {\n  return 1;\n  const x = 2;\n}'
        tree = _make_ts_tree(src)
        violations = _walk(tree.root_node, 'f.ts', src.splitlines())
        assert len(violations) == 1
        fname, _lineno, msg = violations[0]
        assert fname == 'f.ts'
        assert 'unreachable' in msg
        assert 'return' in msg

    def test_throw_before_stmt_is_violation(self) -> None:
        src = 'function f() {\n  throw new Error();\n  const x = 2;\n}'
        tree = _make_ts_tree(src)
        violations = _walk(tree.root_node, 'f.ts', src.splitlines())
        assert len(violations) == 1
        _, _, msg = violations[0]
        assert 'throw' in msg

    def test_break_in_loop_is_violation(self) -> None:
        src = 'function f() {\n  for (let i=0;i<10;i++) {\n    break;\n    console.log(i);\n  }\n}'
        tree = _make_ts_tree(src)
        violations = _walk(tree.root_node, 'f.ts', src.splitlines())
        assert len(violations) == 1

    def test_continue_in_loop_is_violation(self) -> None:
        src = 'function f() {\n  for (let i=0;i<10;i++) {\n    continue;\n    console.log(i);\n  }\n}'
        tree = _make_ts_tree(src)
        violations = _walk(tree.root_node, 'f.ts', src.splitlines())
        assert len(violations) == 1

    def test_disable_comment_suppresses_violation(self) -> None:
        src = 'function f() {\n  return 1;\n  const x = 2; // unreachable-code: disable\n}'
        tree = _make_ts_tree(src)
        assert _walk(tree.root_node, 'f.ts', src.splitlines()) == []

    def test_clean_arrow_function_returns_empty(self) -> None:
        src = 'const f = () => {\n  const x = 1;\n  return x;\n};'
        tree = _make_ts_tree(src)
        assert _walk(tree.root_node, 'f.ts', src.splitlines()) == []


class TestTsUnreachableMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.ts', 'function f() {\n  return 1;\n}\n')
        assert main([f]) == 0

    def test_unreachable_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.ts', 'function f() {\n  return 1;\n  const x = 2;\n}\n')
        assert main([f]) == 1

    def test_tsx_file_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.tsx', 'function f() {\n  throw new Error();\n  return 1;\n}\n')
        assert main([f]) == 1

    def test_jsx_file_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.jsx', 'function f() {\n  return 1;\n  const x = 2;\n}\n')
        assert main([f]) == 1

    def test_js_clean_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.js', 'function f() {\n  return 1;\n}\n')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
