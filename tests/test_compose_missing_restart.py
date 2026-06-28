"""Tests for compose_missing_restart."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.compose_missing_restart import main


def _compose(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'docker-compose.yml'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestComposeMissingRestart:
    def test_missing_restart_flagged(self, tmp_path: Path) -> None:
        body = 'services:\n  api:\n    image: x\n'
        assert main([_compose(tmp_path, body)]) == 1

    def test_wrong_restart_flagged(self, tmp_path: Path) -> None:
        body = 'services:\n  api:\n    image: x\n    restart: always\n'
        assert main([_compose(tmp_path, body)]) == 1

    def test_correct_restart_ok(self, tmp_path: Path) -> None:
        body = 'services:\n  api:\n    image: x\n    restart: unless-stopped\n'
        assert main([_compose(tmp_path, body)]) == 0

    def test_malformed_yaml_skipped(self, tmp_path: Path) -> None:
        assert main([_compose(tmp_path, 'services: [unclosed\n')]) == 0
