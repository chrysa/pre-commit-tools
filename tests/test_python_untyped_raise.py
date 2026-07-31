"""Tests for python_untyped_raise hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.python_untyped_raise import detect_untyped_raise, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


_DOMAIN_RAISE = """\
class OrderError(Exception):
    pass


def cancel(order_id: int) -> None:
    raise OrderError(f'cannot cancel {order_id}')
"""

_BUILTIN_RAISE = """\
def cancel(order_id: int) -> None:
    raise Exception(f'cannot cancel {order_id}')
"""


class TestDetectUntypedRaise:
    def test_domain_exception_returns_empty(self) -> None:
        assert detect_untyped_raise(_DOMAIN_RAISE, 'f.py') == []

    def test_builtin_exception_returns_violation(self) -> None:
        result = detect_untyped_raise(_BUILTIN_RAISE, 'f.py')
        assert len(result) == 1
        assert result[0][1] == 2
        assert 'Exception' in result[0][2]

    def test_runtime_error_returns_violation(self) -> None:
        src = 'def f() -> None:\n    raise RuntimeError("boom")\n'
        assert len(detect_untyped_raise(src, 'f.py')) == 1

    def test_raise_without_call_returns_violation(self) -> None:
        src = 'def f() -> None:\n    raise Exception\n'
        assert len(detect_untyped_raise(src, 'f.py')) == 1

    def test_bare_reraise_returns_empty(self) -> None:
        src = 'def f() -> None:\n    try:\n        g()\n    except ValueError:\n        raise\n'
        assert detect_untyped_raise(src, 'f.py') == []

    def test_raise_from_domain_error_returns_empty(self) -> None:
        src = (
            'class DomainError(Exception):\n    pass\n\n'
            'def f() -> None:\n'
            '    try:\n        g()\n'
            '    except ValueError as exc:\n        raise DomainError("x") from exc\n'
        )
        assert detect_untyped_raise(src, 'f.py') == []

    def test_disable_comment_returns_empty(self) -> None:
        src = 'def f() -> None:\n    raise Exception("boom")  # python-untyped-raise: disable\n'
        assert detect_untyped_raise(src, 'f.py') == []

    def test_syntax_error_returns_empty(self) -> None:
        assert detect_untyped_raise('def broken(:\n', 'f.py') == []


class TestMain:
    def test_clean_file_returns_zero(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'ok.py', _DOMAIN_RAISE)]) == 0

    def test_violating_file_returns_one(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'ko.py', _BUILTIN_RAISE)]) == 1

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'absent.py')]) == 0
