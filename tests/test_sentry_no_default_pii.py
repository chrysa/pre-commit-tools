"""Tests for sentry_no_default_pii."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.sentry_no_default_pii import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestSentryNoDefaultPii:
    def test_true_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'sentry_sdk.init(dsn=DSN, send_default_pii=True)\n')]) == 1

    def test_spaced_true_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '    send_default_pii = True\n')]) == 1

    def test_false_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'sentry_sdk.init(dsn=DSN, send_default_pii=False)\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'send_default_pii=True  # sentry-no-default-pii: disable\n')]) == 0
