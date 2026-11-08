"""Tests for the deprecated-hook registry and its runtime notice."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import yaml

from pre_commit_hooks.print_detection import main as print_main
from pre_commit_hooks.tools.deprecation import DEPRECATED_HOOKS, warn_deprecated

_MANIFEST = Path(__file__).resolve().parent.parent / '.pre-commit-hooks.yaml'


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


def _manifest() -> dict[str, dict[str, str]]:
    hooks = yaml.safe_load(_MANIFEST.read_text(encoding='utf-8'))
    return {hook['id']: hook for hook in hooks}


class TestWarnDeprecated:
    def test_known_hook_writes_notice(self) -> None:
        stream = io.StringIO()
        warn_deprecated(hook_id='python-print-detection', stream=stream)
        output = stream.getvalue()
        assert '[DEPRECATED]' in output
        assert 'T201' in output
        assert 'DEPRECATIONS.md' in output

    def test_unknown_hook_is_silent(self) -> None:
        stream = io.StringIO()
        warn_deprecated(hook_id='not-a-hook', stream=stream)
        assert stream.getvalue() == ''

    def test_defaults_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        warn_deprecated(hook_id='ts-no-any')
        captured = capsys.readouterr()
        assert captured.out == ''
        assert 'no-explicit-any' in captured.err


class TestDeprecatedHookMain:
    def test_exit_code_unchanged_on_violation(self, in_tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = _write(in_tmp_path, 'bad.py', 'print("x")\n')
        assert print_main([f]) == 1
        assert '[DEPRECATED]' in capsys.readouterr().err

    def test_exit_code_unchanged_on_clean_file(self, in_tmp_path: Path) -> None:
        f = _write(in_tmp_path, 'ok.py', 'x = 1\n')
        assert print_main([f]) == 0


class TestManifestConsistency:
    @pytest.mark.parametrize('hook_id', sorted(DEPRECATED_HOOKS))
    def test_registered_hook_exists_and_is_flagged(self, hook_id: str) -> None:
        hook = _manifest()[hook_id]
        assert hook['name'].startswith('[DEPRECATED]')
        assert hook['description'].startswith('DEPRECATED')

    def test_no_unregistered_hook_is_flagged(self) -> None:
        flagged = {hook_id for hook_id, hook in _manifest().items() if '[DEPRECATED]' in hook['name']}
        assert flagged == set(DEPRECATED_HOOKS)

    @pytest.mark.parametrize('hook_id', sorted(DEPRECATED_HOOKS))
    def test_documented_in_deprecations_md(self, hook_id: str) -> None:
        doc = (_MANIFEST.parent / 'DEPRECATIONS.md').read_text(encoding='utf-8')
        assert f'`{hook_id}`' in doc
