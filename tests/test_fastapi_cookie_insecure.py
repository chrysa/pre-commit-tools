"""Tests for fastapi_cookie_insecure."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.fastapi_cookie_insecure import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestFastapiCookieInsecure:
    def test_missing_flags_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'response.set_cookie("session", value)\n')]) == 1

    def test_partial_flags_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'response.set_cookie("session", value, httponly=True)\n')]) == 1

    def test_all_flags_ok(self, tmp_path: Path) -> None:
        body = 'response.set_cookie("s", v, secure=True, httponly=True, samesite="lax")\n'
        assert main([_py(tmp_path, body)]) == 0

    def test_multiline_all_flags_ok(self, tmp_path: Path) -> None:
        body = 'response.set_cookie(\n    "s", v,\n    secure=True,\n    httponly=True,\n    samesite="lax",\n)\n'
        assert main([_py(tmp_path, body)]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'response.set_cookie("s", v)  # cookie-insecure: disable\n')]) == 0
