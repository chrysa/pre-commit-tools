"""Tests for django_cookie_security."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.django_cookie_security import main

_COMPLETE = (
    'SESSION_COOKIE_HTTPONLY = True\n'
    'CSRF_COOKIE_HTTPONLY = True\n'
    'SESSION_COOKIE_SECURE = True\n'
    'CSRF_COOKIE_SECURE = True\n'
    'SESSION_COOKIE_SAMESITE = "Lax"\n'
    'CSRF_COOKIE_SAMESITE = "Lax"\n'
)


def _settings(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'prod.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestDjangoCookieSecurity:
    def test_complete_settings_ok(self, tmp_path: Path) -> None:
        assert main([_settings(tmp_path, _COMPLETE)]) == 0

    def test_missing_flag_flagged(self, tmp_path: Path) -> None:
        body = _COMPLETE.replace('SESSION_COOKIE_HTTPONLY = True\n', '')
        assert main([_settings(tmp_path, body)]) == 1

    def test_flag_set_false_flagged(self, tmp_path: Path) -> None:
        body = _COMPLETE.replace('CSRF_COOKIE_SECURE = True', 'CSRF_COOKIE_SECURE = False')
        assert main([_settings(tmp_path, body)]) == 1
