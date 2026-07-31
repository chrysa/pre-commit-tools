"""Tests for python_mutable_default hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.python_mutable_default import detect_mutable_default, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


@pytest.fixture(autouse=True)
def _cwd_is_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hooks only read inside the working tree, so run mains from tmp_path."""
    monkeypatch.chdir(tmp_path)


_SAFE_DEFAULT = """\
def collect(items: list[str] | None = None) -> list[str]:
    items = items or []
    return items
"""

_MUTABLE_DEFAULT = """\
def collect(items: list[str] = []) -> list[str]:
    return items
"""


class TestDetectMutableDefault:
    def test_none_default_returns_empty(self) -> None:
        assert detect_mutable_default(_SAFE_DEFAULT, 'f.py') == []

    def test_list_literal_returns_violation(self) -> None:
        result = detect_mutable_default(_MUTABLE_DEFAULT, 'f.py')
        assert len(result) == 1
        assert 'list literal' in result[0][2]
        assert 'collect' in result[0][2]

    def test_dict_literal_returns_violation(self) -> None:
        src = 'def f(opts: dict = {}) -> None:\n    pass\n'
        assert len(detect_mutable_default(src, 'f.py')) == 1

    def test_set_call_returns_violation(self) -> None:
        src = 'def f(seen: set = set()) -> None:\n    pass\n'
        assert len(detect_mutable_default(src, 'f.py')) == 1

    def test_keyword_only_default_returns_violation(self) -> None:
        src = 'def f(*, tags: list = []) -> None:\n    pass\n'
        assert len(detect_mutable_default(src, 'f.py')) == 1

    def test_async_function_returns_violation(self) -> None:
        src = 'async def f(items: list = []) -> None:\n    pass\n'
        assert len(detect_mutable_default(src, 'f.py')) == 1

    def test_immutable_defaults_return_empty(self) -> None:
        src = 'def f(a: int = 0, b: str = "x", c: tuple = (), d: bool = False) -> None:\n    pass\n'
        assert detect_mutable_default(src, 'f.py') == []

    def test_disable_comment_returns_empty(self) -> None:
        src = 'def f(items: list = []) -> None:  # python-mutable-default: disable\n    pass\n'
        assert detect_mutable_default(src, 'f.py') == []

    def test_syntax_error_returns_empty(self) -> None:
        assert detect_mutable_default('def broken(:\n', 'f.py') == []


class TestMain:
    def test_clean_file_returns_zero(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'ok.py', _SAFE_DEFAULT)]) == 0

    def test_violating_file_returns_one(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'ko.py', _MUTABLE_DEFAULT)]) == 1

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'absent.py')]) == 0
