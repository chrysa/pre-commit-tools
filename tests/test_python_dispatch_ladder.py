"""Tests for python_dispatch_ladder hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.python_dispatch_ladder import detect_dispatch_ladder, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


_LOOKUP_TABLE = """\
_HANDLERS = {'a': handle_a, 'b': handle_b, 'c': handle_c, 'd': handle_d}


def dispatch(kind: str):
    return _HANDLERS[kind]()
"""

_LADDER = """\
def dispatch(kind: str):
    if kind == 'a':
        return handle_a()
    elif kind == 'b':
        return handle_b()
    elif kind == 'c':
        return handle_c()
    elif kind == 'd':
        return handle_d()
    return None
"""

_UNRELATED_CONDITIONS = """\
def check(user, order, cart):
    if user.is_anonymous:
        return 'anon'
    elif order.total > 100:
        return 'big'
    elif cart.is_empty:
        return 'empty'
    elif user.is_staff:
        return 'staff'
    return 'other'
"""


class TestDetectDispatchLadder:
    def test_lookup_table_returns_empty(self) -> None:
        assert detect_dispatch_ladder(_LOOKUP_TABLE, 'f.py') == []

    def test_ladder_returns_violation(self) -> None:
        result = detect_dispatch_ladder(_LADDER, 'f.py')
        assert len(result) == 1
        assert result[0][1] == 2
        assert 'lookup table' in result[0][2]

    def test_unrelated_conditions_return_empty(self) -> None:
        assert detect_dispatch_ladder(_UNRELATED_CONDITIONS, 'f.py') == []

    def test_short_ladder_returns_empty(self) -> None:
        src = "def f(k):\n    if k == 'a':\n        return 1\n    elif k == 'b':\n        return 2\n    return 0\n"
        assert detect_dispatch_ladder(src, 'f.py') == []

    def test_attribute_subject_returns_violation(self) -> None:
        src = (
            'def f(self):\n'
            "    if self.status == 'a':\n        return 1\n"
            "    elif self.status == 'b':\n        return 2\n"
            "    elif self.status == 'c':\n        return 3\n"
            "    elif self.status == 'd':\n        return 4\n"
            '    return 0\n'
        )
        assert len(detect_dispatch_ladder(src, 'f.py')) == 1

    def test_in_membership_ladder_returns_violation(self) -> None:
        src = (
            'def f(k):\n'
            "    if k in ('a', 'b'):\n        return 1\n"
            "    elif k in ('c',):\n        return 2\n"
            "    elif k in ('d',):\n        return 3\n"
            "    elif k in ('e',):\n        return 4\n"
            '    return 0\n'
        )
        assert len(detect_dispatch_ladder(src, 'f.py')) == 1

    def test_custom_threshold_flags_shorter_ladder(self) -> None:
        src = "def f(k):\n    if k == 'a':\n        return 1\n    elif k == 'b':\n        return 2\n    return 0\n"
        assert len(detect_dispatch_ladder(src, 'f.py', max_branches=1)) == 1

    def test_ladder_counted_once_not_per_elif(self) -> None:
        assert len(detect_dispatch_ladder(_LADDER, 'f.py')) == 1

    def test_disable_comment_returns_empty(self) -> None:
        src = _LADDER.replace(
            "    if kind == 'a':",
            "    if kind == 'a':  # python-dispatch-ladder: disable",
        )
        assert detect_dispatch_ladder(src, 'f.py') == []

    def test_syntax_error_returns_empty(self) -> None:
        assert detect_dispatch_ladder('def broken(:\n', 'f.py') == []


class TestMain:
    def test_clean_file_returns_zero(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'ok.py', _LOOKUP_TABLE)]) == 0

    def test_violating_file_returns_one(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'ko.py', _LADDER)]) == 1

    def test_threshold_flag_is_honoured(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'ko.py', _LADDER)
        assert main(['--max-branches', '10', path]) == 0

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'absent.py')]) == 0
