"""Tests for os_environ_direct."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.os_environ_direct import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestOsEnvironDirect:
    def test_os_environ_subscript_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'token = os.environ["TOKEN"]\n')]) == 1

    def test_os_getenv_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'token = os.getenv("TOKEN")\n')]) == 1

    def test_settings_object_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'token = settings.token\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'x = os.getenv("X")  # os-environ-direct: disable\n')]) == 0
