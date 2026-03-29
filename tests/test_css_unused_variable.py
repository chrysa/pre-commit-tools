"""Tests for css_unused_variable."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.css_unused_variable import detect_unused_variables, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectUnusedVariables:
    def test_used_variable_ok(self) -> None:
        css = ':root {\n  --color-primary: red;\n}\n.foo {\n  color: var(--color-primary);\n}\n'
        assert detect_unused_variables(css, 'a.css') == []

    def test_unused_variable_detected(self) -> None:
        css = ':root {\n  --color-unused: red;\n}\n.foo {\n  color: blue;\n}\n'
        violations = detect_unused_variables(css, 'a.css')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'color-unused' in msg

    def test_multiple_unused_detected(self) -> None:
        css = ':root {\n  --a: 1;\n  --b: 2;\n}\n.foo { color: blue; }\n'
        violations = detect_unused_variables(css, 'a.css')
        assert len(violations) == 2

    def test_partial_usage_detected(self) -> None:
        css = ':root {\n  --used: 1;\n  --unused: 2;\n}\n.foo { color: var(--used); }\n'
        violations = detect_unused_variables(css, 'a.css')
        assert len(violations) == 1
        assert 'unused' in violations[0][2]

    def test_in_block_comment_not_counted(self) -> None:
        css = '.foo {\n  /* --ghost: red; */\n  color: blue;\n}\n'
        assert detect_unused_variables(css, 'a.css') == []

    def test_disable_comment_suppresses(self) -> None:
        css = ':root {\n  --x: 1; /* css-unused-variable: disable */\n}\n.foo { color: blue; }\n'
        assert detect_unused_variables(css, 'a.css') == []


class TestCssUnusedVariableMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.css', ':root {\n  --c: red;\n}\n.foo { color: var(--c); }\n')
        assert main([f]) == 0

    def test_unused_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.css', ':root {\n  --orphan: red;\n}\n.foo { color: blue; }\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
