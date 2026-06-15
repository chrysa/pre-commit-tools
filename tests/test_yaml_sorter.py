"""Tests for yaml_sorter."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

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

    def test_list_of_scalars_preserved(self) -> None:
        """Scalar sequences keep their original order (YAML sequences are ordered)."""
        data = {'items': ['c', 'a', 'b']}
        _changed, result = sort_yaml_file(False, data, {})
        assert result['items'] == ['c', 'a', 'b']
        assert not _changed

    def test_list_of_dicts_not_sorted(self) -> None:
        """Lists containing dicts should be left as-is."""
        inner = [{'z': 1}, {'a': 2}]
        data = {'items': inner}
        _changed, result = sort_yaml_file(False, data, {})
        assert result['items'] == inner

    def test_healthcheck_sequence_order_preserved(self) -> None:
        """Regression: order-sensitive sequences (e.g. docker-compose healthcheck.test)
        must keep their exact order while sibling mapping keys are still sorted.
        """
        data = {'healthcheck': {'test': ['CMD', 'curl', '-f', 'http://x/health']}}
        _changed, result = sort_yaml_file(False, data, {})
        assert result['healthcheck']['test'] == ['CMD', 'curl', '-f', 'http://x/health']
        assert not _changed


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


class TestWorkflowCorruptionGuard:
    """Issue #215 — yaml-sorter must never touch GitHub Actions workflows."""

    def test_on_key_is_corrupted_to_true_when_rewritten(self, tmp_path: Path) -> None:
        """Characterizes WHY workflows are excluded: PyYAML (YAML 1.1) coerces the
        top-level `on:` trigger key to the boolean True and re-serializes it as
        `true:`, silently removing the workflow's triggers. This is the corruption
        the hook-level exclude protects against; if the sorter is ever made
        YAML-1.2-safe, this test should be replaced by an `on:`-preserving one.
        """
        # `jobs` before `on` so alphabetical sorting forces a rewrite.
        wf = _write(
            tmp_path,
            'wf.yaml',
            'jobs:\n  a:\n    runs-on: ubuntu-latest\non:\n  push:\n    branches: [main]\n',
        )
        assert main([wf]) == 1  # keys reordered -> file rewritten
        rewritten = Path(wf).read_text()
        assert 'true:' in rewritten  # `on:` was coerced to the boolean True
        # the workflow no longer has a usable top-level trigger key
        assert True in yaml.safe_load(rewritten)

    def test_hook_definition_excludes_workflows(self) -> None:
        """The yaml-sorter hook must carry an `exclude` that matches
        `.github/workflows/` so consumers never corrupt their workflows.
        """
        hooks_file = Path(__file__).parents[1] / '.pre-commit-hooks.yaml'
        hooks = yaml.safe_load(hooks_file.read_text())
        sorter = next(h for h in hooks if h['id'] == 'yaml-sorter')
        assert 'exclude' in sorter, 'yaml-sorter must exclude unsafe paths'
        assert re.search(sorter['exclude'], '.github/workflows/ci.yml'), (
            f'exclude {sorter["exclude"]!r} must match GitHub workflow paths'
        )
