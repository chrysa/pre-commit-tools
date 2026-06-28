"""Tests for pii_hardcoded."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.pii_hardcoded import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestPiiHardcoded:
    def test_nir_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'NIR = "183059912345678"\n')]) == 1

    def test_iban_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'IBAN = "FR7630006000011234567890189"\n')]) == 1

    def test_real_email_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'owner = "jean.dupont@gmail.com"\n')]) == 1

    def test_example_email_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'owner = "user@example.com"\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'owner = "jean.dupont@gmail.com"  # pii-hardcoded: disable\n')]) == 0
