"""Tests for json_sorter."""

from __future__ import annotations

import json
from pathlib import Path

from pre_commit_hooks.json_sorter import main, sort_json


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestSortJson:
    def test_dict_sorted(self) -> None:
        assert list(sort_json({'b': 1, 'a': 2}).keys()) == ['a', 'b']  # type: ignore[union-attr]

    def test_nested_dict_sorted(self) -> None:
        result = sort_json({'z': {'b': 1, 'a': 2}})
        assert list(result['z'].keys()) == ['a', 'b']  # type: ignore[index]

    def test_list_preserved(self) -> None:
        data = [3, 1, 2]
        assert sort_json(data) == [3, 1, 2]

    def test_scalar_returned(self) -> None:
        assert sort_json(42) == 42  # type: ignore[comparison-overlap]


class TestJsonSorterMain:
    def test_sorted_file_returns_0(self, tmp_path: Path) -> None:
        content = json.dumps({'a': 1, 'b': 2}, indent=2) + '\n'
        f = _write(tmp_path, 's.json', content)
        assert main([f]) == 0

    def test_unsorted_file_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        content = json.dumps({'b': 2, 'a': 1}, indent=2) + '\n'
        f = _write(tmp_path, 'u.json', content)
        assert main([f]) == 1
        rewritten = json.loads(Path(f).read_text())
        assert list(rewritten.keys()) == ['a', 'b']

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
