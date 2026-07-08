"""Tests for ignore_file_sorter."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

from pre_commit_hooks.ignore_file_sorter import main, sort_ignore_lines


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestSortIgnoreLines:
    def test_sorted_unchanged(self) -> None:
        assert sort_ignore_lines(['*.log', '*.tmp']) == ['*.log', '*.tmp']

    def test_unsorted_sorted(self) -> None:
        assert sort_ignore_lines(['*.tmp', '*.log']) == ['*.log', '*.tmp']

    def test_case_insensitive(self) -> None:
        assert sort_ignore_lines(['Zebra', 'apple']) == ['apple', 'Zebra']

    def test_comments_are_anchors(self) -> None:
        lines = ['# build', 'dist', 'build', '# vcs', '.git']
        assert sort_ignore_lines(lines) == ['# build', 'build', 'dist', '# vcs', '.git']

    def test_blank_lines_preserved_as_anchors(self) -> None:
        lines = ['b', 'a', '', 'd', 'c']
        assert sort_ignore_lines(lines) == ['a', 'b', '', 'c', 'd']

    def test_negation_uses_stripped_key(self) -> None:
        # '!keep.log' sorts as 'keep.log', landing next to 'keep.log'.
        lines = ['zzz', '!keep.log', 'keep.log']
        assert sort_ignore_lines(lines) == ['!keep.log', 'keep.log', 'zzz']

    def test_empty_input(self) -> None:
        assert sort_ignore_lines([]) == []


class TestIgnoreFileSorterMain:
    def test_already_sorted_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '.gitignore', '*.log\n*.tmp\n')
        assert main([f]) == 0

    def test_unsorted_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '.gitignore', '*.tmp\n*.log\n')
        assert main([f]) == 1
        assert Path(f).read_text(encoding='utf-8') == '*.log\n*.tmp\n'

    def test_trailing_newline_preserved_when_absent(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '.gitignore', 'b\na')
        assert main([f]) == 1
        assert Path(f).read_text(encoding='utf-8') == 'a\nb'

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0


def _make_reverse_script(tmp_path: Path) -> str:
    """Create an executable script that reverse-sorts stdin lines to stdout."""
    script = tmp_path / 'reverse_sort'
    script.write_text(
        f'#!{sys.executable}\n'
        'import sys\n'
        'lines = sys.stdin.read().splitlines()\n'
        'print("\\n".join(sorted(lines, reverse=True)))\n',
        encoding='utf-8',
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


class TestIgnoreFileSorterCustomScript:
    def test_custom_script_overrides_default_order(self, tmp_path: Path) -> None:
        script = _make_reverse_script(tmp_path)
        f = _write(tmp_path, '.gitignore', 'a\nb\nc\n')
        assert main(['--sort-script', script, f]) == 1
        assert Path(f).read_text(encoding='utf-8') == 'c\nb\na\n'

    def test_custom_script_already_ordered_returns_0(self, tmp_path: Path) -> None:
        script = _make_reverse_script(tmp_path)
        f = _write(tmp_path, '.gitignore', 'c\nb\na\n')
        assert main(['--sort-script', script, f]) == 0

    def test_custom_script_receives_filename_as_argv1(self, tmp_path: Path) -> None:
        script = tmp_path / 'echo_name'
        script.write_text(
            f'#!{sys.executable}\nimport sys\nsys.stdin.read()\nprint(sys.argv[1])\n',
            encoding='utf-8',
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        f = _write(tmp_path, '.gitignore', 'x\n')
        assert main(['--sort-script', str(script), f]) == 1
        assert Path(f).read_text(encoding='utf-8').strip() == f
