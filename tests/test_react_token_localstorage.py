"""Tests for react_token_localstorage."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.react_token_localstorage import main


def _ts(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'a.ts'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestReactTokenLocalStorage:
    def test_token_key_flagged(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, 'localStorage.setItem("access_token", t)\n')]) == 1

    def test_jwt_key_flagged(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, "localStorage.setItem('jwt', t)\n")]) == 1

    def test_non_token_key_ok(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, 'localStorage.setItem("theme", "dark")\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, 'localStorage.setItem("token", t)  // token-localstorage: disable\n')]) == 0
