"""Tests for makefile_sorter."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.makefile_sorter import main, sort_makefile


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestSortMakefile:
    def test_rules_sorted_by_target(self) -> None:
        content = 'build:\n\techo build\n\nclean:\n\techo clean\n\napple:\n\techo apple\n'
        result = sort_makefile(content)
        assert result.index('apple:') < result.index('build:') < result.index('clean:')

    def test_recipe_stays_with_target(self) -> None:
        content = 'b:\n\techo B\n\na:\n\techo A\n'
        assert sort_makefile(content) == 'a:\n\techo A\n\nb:\n\techo B\n'

    def test_leading_comment_moves_with_rule(self) -> None:
        content = '# builds it\nbuild:\n\techo build\n\n# always clean\napple:\n\techo apple\n'
        result = sort_makefile(content)
        assert result.index('# always clean') < result.index('# builds it')

    def test_variables_and_phony_keep_position(self) -> None:
        content = 'CC = gcc\n\n.PHONY: build clean\n\nbuild:\n\techo build\n\napple:\n\techo apple\n'
        result = sort_makefile(content)
        assert result.startswith('CC = gcc\n\n.PHONY: build clean\n')
        assert result.index('apple:') < result.index('build:')

    def test_multiple_targets_sorted_by_first(self) -> None:
        content = 'zeta beta:\n\techo z\n\nalpha:\n\techo a\n'
        result = sort_makefile(content)
        assert result.index('alpha:') < result.index('zeta beta:')

    def test_already_sorted_is_unchanged(self) -> None:
        content = 'a:\n\techo A\n\nb:\n\techo B\n'
        assert sort_makefile(content) == content

    def test_no_trailing_newline_preserved(self) -> None:
        content = 'b:\n\techo B\n\na:\n\techo A'
        assert sort_makefile(content) == 'a:\n\techo A\n\nb:\n\techo B'

    def test_prerequisite_continuation_kept(self) -> None:
        content = 'zzz: dep1 \\\n      dep2\n\tbuild\n\naaa:\n\tgo\n'
        result = sort_makefile(content)
        assert result.index('aaa:') < result.index('zzz:')
        assert 'dep2' in result


class TestMakefileSorterMain:
    def test_sorted_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Makefile', 'a:\n\techo A\n\nb:\n\techo B\n')
        assert main([f]) == 0

    def test_unsorted_file_returns_1_and_rewrites(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Makefile', 'b:\n\techo B\n\na:\n\techo A\n')
        assert main([f]) == 1
        rewritten = Path(f).read_text(encoding='utf-8')
        assert rewritten.index('a:') < rewritten.index('b:')

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
