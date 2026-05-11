"""Tests for no_debug_in_settings and django_no_raw_sql hooks."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.django_no_raw_sql import main as main_raw_sql
from pre_commit_hooks.no_debug_in_settings import main as main_debug


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestNoDebugInSettings:
    def test_debug_true_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'settings.py', 'DEBUG = True\n')
        assert main_debug([f]) == 1

    def test_debug_false_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'settings.py', 'DEBUG = False\n')
        assert main_debug([f]) == 0

    def test_commented_debug_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'settings.py', '# DEBUG = True\n')
        assert main_debug([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'settings.py',
            'DEBUG = True  # no-debug-in-settings: disable\n',
        )
        assert main_debug([f]) == 0

    def test_indented_debug_detected(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'settings.py', '    DEBUG = True\n')
        assert main_debug([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main_debug([]) == 0


class TestDjangoNoRawSql:
    def test_raw_call_returns_1(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'views.py',
            "User.objects.raw('SELECT * FROM auth_user')\n",
        )
        assert main_raw_sql([f]) == 1

    def test_cursor_execute_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'views.py', "cursor.execute('SELECT 1')\n")
        assert main_raw_sql([f]) == 1

    def test_clean_queryset_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'views.py', 'User.objects.filter(active=True)\n')
        assert main_raw_sql([f]) == 0

    def test_commented_raw_ignored(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'views.py',
            "# User.objects.raw('SELECT * FROM auth_user')\n",
        )
        assert main_raw_sql([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'views.py',
            'cursor.execute(sql)  # django-no-raw-sql: disable\n',
        )
        assert main_raw_sql([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main_raw_sql([]) == 0
