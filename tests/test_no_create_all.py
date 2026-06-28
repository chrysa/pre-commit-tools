"""Tests for no_create_all."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_create_all import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestNoCreateAll:
    def test_metadata_create_all_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'Base.metadata.create_all(bind=engine)\n')]) == 1

    def test_bare_create_all_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '    db.create_all()\n')]) == 1

    def test_unrelated_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'result = service.create_all_widgets()\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'Base.metadata.create_all()  # no-create-all: disable\n')]) == 0
