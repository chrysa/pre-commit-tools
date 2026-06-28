"""Tests for pii_in_logs."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.pii_in_logs import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestPiiInLogs:
    def test_logger_email_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logger.info(f"user email {user.email}")\n')]) == 1

    def test_logging_password_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logging.debug("password=" + password)\n')]) == 1

    def test_log_without_pii_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logger.info(f"user {user.id} logged in")\n')]) == 0

    def test_non_log_line_with_pii_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'email = request.json["email"]\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logger.info(user.email)  # pii: disable\n')]) == 0

    def test_fingerprint_not_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'device_fingerprint(token_hash)\n')]) == 0
