"""Tests for dead_code_detection (requires vulture for integration tests)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pre_commit_hooks.dead_code_detection import (
    _filter_dynamic,
    _item_key,
    collect_dynamic_names,
    is_test_file,
    main,
)


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDeadCodeDetectionMain:
    def test_missing_vulture_returns_1(self) -> None:
        with patch.dict('sys.modules', {'vulture': None}):
            result = main([])
        assert result == 1

    def test_no_unused_code_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'def used() -> int:\n    return 1\nused()\n')
        # vulture may or may not be installed in CI — skip if absent
        pytest.importorskip('vulture')
        assert main([f]) == 0

    def test_unused_function_returns_1(self, tmp_path: Path) -> None:
        """Unused function with 100% confidence should be reported."""
        pytest.importorskip('vulture')
        f = _write(tmp_path, 'dead.py', 'def _never_called() -> None:\n    pass\n')
        # vulture confidence may vary; mock get_unused_code to force a result
        mock_item = MagicMock()
        mock_item.filename = str(f)
        mock_item.first_lineno = 1
        mock_item.typ = 'function'
        mock_item.name = '_never_called'

        import vulture as vlt

        with patch.object(vlt.Vulture, 'get_unused_code', return_value=[mock_item]):
            result = main(['--min-confidence=60', f])
        assert result == 1

    def test_empty_args_with_vulture_returns_0(self) -> None:
        pytest.importorskip('vulture')
        assert main([]) == 0


class TestCollectDynamicNames:
    @pytest.mark.parametrize(
        ('content', 'expected'),
        [
            ('import importlib\nimportlib.import_module("pkg.sub")\n', {'pkg.sub', 'sub'}),
            ('__import__("pkg.mod")\n', {'pkg.mod', 'mod'}),
            ('getattr(obj, "Handler")\n', {'Handler'}),
            ('setattr(obj, "value", 1)\n', {'value'}),
            ('hasattr(obj, "flag")\n', {'flag'}),
            ('globals()["Plugin"]\n', {'Plugin'}),
            ('vars()["thing"]\n', {'thing'}),
            ('locals()["local_name"]\n', {'local_name'}),
            ('entry_points(group="my.plugins")\n', {'my.plugins', 'plugins'}),
        ],
    )
    def test_patterns(self, tmp_path: Path, content: str, expected: set[str]) -> None:
        f = _write(tmp_path, 'src.py', content)
        assert expected <= collect_dynamic_names([f])

    def test_syntax_error_file_is_skipped(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'broken.py', 'def (:\n')
        assert collect_dynamic_names([f]) == set()

    def test_non_string_getattr_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'src.py', 'getattr(obj, variable)\n')
        assert collect_dynamic_names([f]) == set()

    def test_directory_is_expanded(self, tmp_path: Path) -> None:
        _write(tmp_path, 'pkg/a.py', 'getattr(o, "alpha")\n')
        _write(tmp_path, 'pkg/b.py', 'getattr(o, "beta")\n')
        names = collect_dynamic_names([str(tmp_path / 'pkg')])
        assert {'alpha', 'beta'} <= names


class TestIsTestFile:
    @pytest.mark.parametrize(
        'path',
        [
            'tests/test_x.py',
            'src/tests/helpers.py',
            'test_module.py',
            'module_test.py',
            'conftest.py',
            'app/conftest.py',
        ],
    )
    def test_test_paths(self, path: str) -> None:
        assert is_test_file(path) is True

    @pytest.mark.parametrize('path', ['src/app.py', 'pkg/handler.py', 'main.py'])
    def test_prod_paths(self, path: str) -> None:
        assert is_test_file(path) is False

    def test_custom_pattern(self) -> None:
        assert is_test_file('spec/foo.py', patterns=['spec/']) is True
        assert is_test_file('src/foo.py', patterns=['spec/']) is False


class TestFilterDynamic:
    def test_filters_matching_names(self) -> None:
        items = [SimpleNamespace(name='Plugin'), SimpleNamespace(name='Real')]
        filtered = _filter_dynamic(items, {'Plugin'})
        assert [i.name for i in filtered] == ['Real']

    def test_empty_dynamic_set_is_noop(self) -> None:
        items = [SimpleNamespace(name='Plugin')]
        assert _filter_dynamic(items, set()) is items

    def test_item_key(self) -> None:
        item = SimpleNamespace(filename='a.py', name='x', first_lineno=3)
        assert _item_key(item) == ('a.py', 'x', 3)


class TestDynamicImportSuppression:
    # vulture does not treat a globals() subscript as a usage, but our collector does.
    _SRC = 'class Widget:\n    pass\n\n\nvalue = globals()["Widget"]\nprint(value)\n'

    def test_dynamic_name_not_reported_by_default(self, tmp_path: Path) -> None:
        pytest.importorskip('vulture')
        f = _write(tmp_path, 'plugin.py', self._SRC)
        assert main(['--min-confidence=60', f]) == 0

    def test_dynamic_name_reported_when_disabled(self, tmp_path: Path) -> None:
        pytest.importorskip('vulture')
        f = _write(tmp_path, 'plugin.py', self._SRC)
        assert main(['--min-confidence=60', '--no-dynamic-imports', f]) == 1


class TestTestOnlyDetection:
    def test_test_only_symbol_fails(self, tmp_path: Path) -> None:
        pytest.importorskip('vulture')
        prod = _write(
            tmp_path,
            'helpers.py',
            'def helper_for_tests() -> int:\n    return 42\n',
        )
        test = _write(
            tmp_path,
            'tests/test_helpers.py',
            'from helpers import helper_for_tests\n\n\ndef test_it() -> None:\n    assert helper_for_tests() == 42\n',
        )
        assert main(['--min-confidence=0', '--detect-test-only', prod, test]) == 1

    def test_test_only_warn_only_passes(self, tmp_path: Path) -> None:
        pytest.importorskip('vulture')
        prod = _write(
            tmp_path,
            'helpers.py',
            'def helper_for_tests() -> int:\n    return 42\n',
        )
        test = _write(
            tmp_path,
            'tests/test_helpers.py',
            'from helpers import helper_for_tests\n\n\ndef test_it() -> None:\n    assert helper_for_tests() == 42\n',
        )
        result = main(
            ['--min-confidence=0', '--detect-test-only', '--warn-only', prod, test],
        )
        assert result == 0

    def test_real_dead_code_fails_even_with_warn_only(self, tmp_path: Path) -> None:
        pytest.importorskip('vulture')
        prod = _write(
            tmp_path,
            'helpers.py',
            'def never_used_anywhere() -> int:\n    return 1\n',
        )
        result = main(
            ['--min-confidence=0', '--detect-test-only', '--warn-only', prod],
        )
        assert result == 1
