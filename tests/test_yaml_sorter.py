"""Tests for yaml_sorter."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.yaml_sorter import main, sort_yaml_file


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestSortYamlFile:
    def test_already_sorted_returns_no_change(self) -> None:
        data = {'a': 1, 'b': 2, 'c': 3}
        _changed, result = sort_yaml_file(False, data, {})
        assert not _changed
        assert list(result.keys()) == ['a', 'b', 'c']

    def test_unsorted_returns_change(self) -> None:
        data = {'c': 3, 'a': 1, 'b': 2}
        _changed, result = sort_yaml_file(False, data, {})
        assert _changed
        assert list(result.keys()) == ['a', 'b', 'c']

    def test_nested_dict_sorted(self) -> None:
        data = {'z': {'b': 1, 'a': 2}}
        _changed, result = sort_yaml_file(False, data, {})
        assert list(result['z'].keys()) == ['a', 'b']

    def test_bool_keys_do_not_raise(self) -> None:
        """Regression test for issue #37 — YAML booleans as dict keys."""
        data = {True: 'yes', False: 'no'}
        # Should not raise TypeError
        _changed, result = sort_yaml_file(False, data, {})
        assert isinstance(result, dict)

    def test_mixed_type_keys_do_not_raise(self) -> None:
        """Regression test for issue #37 — mixed-type keys."""
        data = {1: 'int', 'b': 'str', None: 'null'}
        _changed, result = sort_yaml_file(False, data, {})
        assert isinstance(result, dict)

    def test_list_of_scalars_sorted(self) -> None:
        data = {'items': ['c', 'a', 'b']}
        _changed, result = sort_yaml_file(False, data, {})
        assert result['items'] == ['a', 'b', 'c']

    def test_list_of_dicts_not_sorted(self) -> None:
        """Lists containing dicts should be left as-is."""
        inner = [{'z': 1}, {'a': 2}]
        data = {'items': inner}
        _changed, result = sort_yaml_file(False, data, {})
        assert result['items'] == inner


class TestYamlSorterMain:
    def test_sorted_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'sorted.yaml', 'a: 1\nb: 2\n')
        assert main([f]) == 0

    def test_unsorted_file_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'unsorted.yaml', 'b: 2\na: 1\n')
        assert main([f]) == 1
        content = Path(f).read_text()
        assert content.index('a:') < content.index('b:')

    def test_non_dict_yaml_skipped(self, tmp_path: Path) -> None:
        """YAML files whose root is not a dict (e.g. a list) are silently skipped."""
        f = _write(tmp_path, 'list.yaml', '- a\n- b\n')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
