"""Tests for requirements_sort."""
from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.requirements_sort import main, sort_requirements


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestSortRequirements:
    def test_sorted_unchanged(self) -> None:
        lines = ['requests', 'urllib3']
        assert sort_requirements(lines) == ['requests', 'urllib3']

    def test_unsorted_sorted(self) -> None:
        lines = ['urllib3', 'requests']
        assert sort_requirements(lines) == ['requests', 'urllib3']

    def test_comments_first(self) -> None:
        lines = ['urllib3', '# comment', 'requests']
        result = sort_requirements(lines)
        assert result[0] == '# comment'
        assert result[1:] == ['requests', 'urllib3']

    def test_blank_lines_first(self) -> None:
        lines = ['urllib3', '', 'requests']
        result = sort_requirements(lines)
        assert result[0] == ''
        assert result[1:] == ['requests', 'urllib3']

    def test_case_insensitive(self) -> None:
        lines = ['Urllib3', 'requests']
        result = sort_requirements(lines)
        assert result == ['requests', 'Urllib3']


class TestRequirementsSortMain:
    def test_already_sorted_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'req.txt', 'requests\nurllib3\n')
        assert main([f]) == 0

    def test_unsorted_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'req.txt', 'urllib3\nrequests\n')
        assert main([f]) == 1
        lines = Path(f).read_text().splitlines()
        assert lines[0] == 'requests'
        assert lines[1] == 'urllib3'

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
