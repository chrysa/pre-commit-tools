"""Tests for no_console_warn, react_direct_dom, and import_no_relative_parent hooks."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.import_no_relative_parent import main as main_import
from pre_commit_hooks.no_console_warn import main as main_warn
from pre_commit_hooks.react_direct_dom import main as main_dom


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestNoConsoleWarn:
    def test_console_warn_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.js', 'console.warn("oops");\n')
        assert main_warn([f]) == 1

    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.js', 'console.log("hi");\n')
        assert main_warn([f]) == 0

    def test_commented_line_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', '// console.warn("debug");\n')
        assert main_warn([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', 'console.warn("x"); // no-console-warn: disable\n')
        assert main_warn([f]) == 0

    def test_indented_call_detected(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.tsx', '  console.warn("nested");\n')
        assert main_warn([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main_warn([]) == 0


class TestReactDirectDom:
    def test_get_element_by_id_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', 'const el = document.getElementById("foo");\n')
        assert main_dom([f]) == 1

    def test_query_selector_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', 'const el = document.querySelector(".foo");\n')
        assert main_dom([f]) == 1

    def test_query_selector_all_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', 'document.querySelectorAll("div");\n')
        assert main_dom([f]) == 1

    def test_get_elements_by_class_name_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', 'document.getElementsByClassName("cls");\n')
        assert main_dom([f]) == 1

    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', 'const x = useRef(null);\n')
        assert main_dom([f]) == 0

    def test_commented_line_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', '// document.getElementById("x");\n')
        assert main_dom([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Comp.tsx', 'document.getElementById("x"); // react-direct-dom: disable\n')
        assert main_dom([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main_dom([]) == 0


class TestImportNoRelativeParent:
    def test_two_level_import_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', "import { foo } from '../../components/Foo';\n")
        assert main_import([f]) == 1

    def test_three_level_import_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', "import { bar } from '../../../utils';\n")
        assert main_import([f]) == 1

    def test_single_level_import_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', "import { foo } from '../sibling';\n")
        assert main_import([f]) == 0

    def test_alias_import_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', "import { foo } from '@/components/Foo';\n")
        assert main_import([f]) == 0

    def test_require_deep_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.js', "const x = require('../../lib/utils');\n")
        assert main_import([f]) == 1

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', "import { x } from '../../foo'; // import-no-relative-parent: disable\n")
        assert main_import([f]) == 0

    def test_commented_import_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', "// import { x } from '../../foo';\n")
        assert main_import([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main_import([]) == 0
