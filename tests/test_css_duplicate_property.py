"""Tests for css_duplicate_property_detection."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.css_duplicate_property_detection import (
    detect_duplicate_ids,
    detect_duplicate_properties,
    main,
)


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectDuplicateProperties:
    def test_no_duplicate_returns_empty(self) -> None:
        css = '.foo {\n  color: red;\n  margin: 0;\n}\n'
        assert detect_duplicate_properties(css, 'a.css') == []

    def test_duplicate_property_detected(self) -> None:
        css = '.foo {\n  color: red;\n  color: blue;\n}\n'
        violations = detect_duplicate_properties(css, 'a.css')
        assert len(violations) == 1
        fname, dup_line, first_line, prop = violations[0]
        assert fname == 'a.css'
        assert prop == 'color'
        assert first_line == 2
        assert dup_line == 3

    def test_duplicate_in_different_rules_ok(self) -> None:
        css = '.foo {\n  color: red;\n}\n.bar {\n  color: blue;\n}\n'
        assert detect_duplicate_properties(css, 'a.css') == []

    def test_duplicate_in_nested_rule_detected(self) -> None:
        css = '.foo {\n  color: red;\n  .bar {\n    margin: 0;\n    margin: 10px;\n  }\n}\n'
        violations = detect_duplicate_properties(css, 'a.css')
        # margin duplicate is in nested rule
        assert any(v[3] == 'margin' for v in violations)

    def test_disable_comment_suppresses_violation(self) -> None:
        css = '.foo {\n  color: red;\n  color: blue; /* css-duplicate-property: disable */\n}\n'
        assert detect_duplicate_properties(css, 'a.css') == []

    def test_block_comment_stripped_correctly(self) -> None:
        css = '.foo {\n  /* color: red; */\n  color: blue;\n}\n'
        assert detect_duplicate_properties(css, 'a.css') == []

    def test_multiple_duplicates_reported(self) -> None:
        css = '.foo {\n  color: red;\n  margin: 0;\n  color: blue;\n  margin: 10px;\n}\n'
        violations = detect_duplicate_properties(css, 'a.css')
        props = {v[3] for v in violations}
        assert 'color' in props
        assert 'margin' in props

    def test_pseudo_class_not_mistaken_for_property(self) -> None:
        css = 'a {\n  color: red;\n}\na:hover {\n  color: blue;\n}\n'
        assert detect_duplicate_properties(css, 'a.css') == []


class TestCssDuplicatePropertyMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.css', '.foo {\n  color: red;\n}\n')
        assert main([f]) == 0

    def test_duplicate_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.css', '.foo {\n  color: red;\n  color: blue;\n}\n')
        assert main([f]) == 1

    def test_duplicate_id_returns_1(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'bad.css',
            '#hero {\n  color: red;\n}\n#hero {\n  color: blue;\n}\n',
        )
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0


class TestDetectDuplicateIds:
    def test_no_duplicate_returns_empty(self) -> None:
        css = '#foo {\n  color: red;\n}\n#bar {\n  color: blue;\n}\n'
        assert detect_duplicate_ids(css, 'a.css') == []

    def test_duplicate_id_detected(self) -> None:
        css = '#foo {\n  color: red;\n}\n#foo {\n  color: blue;\n}\n'
        violations = detect_duplicate_ids(css, 'a.css')
        assert len(violations) == 1
        fname, dup_line, first_line, id_name = violations[0]
        assert fname == 'a.css'
        assert id_name == 'foo'
        assert first_line == 1
        assert dup_line == 4

    def test_id_in_compound_selector(self) -> None:
        css = 'div#foo {\n  color: red;\n}\ndiv#foo:hover {\n  color: blue;\n}\n'
        violations = detect_duplicate_ids(css, 'a.css')
        assert len(violations) == 1

    def test_disable_comment_suppresses(self) -> None:
        css = '#foo {\n  color: red;\n}\n#foo { /* css-duplicate-id: disable */\n  color: blue;\n}\n'
        assert detect_duplicate_ids(css, 'a.css') == []

    def test_unique_ids_clean(self) -> None:
        css = '#nav {\n  display: flex;\n}\n#footer {\n  display: block;\n}\n'
        assert detect_duplicate_ids(css, 'a.css') == []
