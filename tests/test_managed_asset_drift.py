"""Tests for managed_asset_drift."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.managed_asset_drift import main


def _skill(root: Path, name: str, body: str) -> None:
    d = root / '.claude' / 'skills' / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'SKILL.md').write_text(body, encoding='utf-8')


def _agent(root: Path, name: str, body: str) -> None:
    d = root / '.claude' / 'agents'
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{name}.md').write_text(body, encoding='utf-8')


class TestManagedAssetDrift:
    def test_no_source_skips(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('STD_ROOT', raising=False)
        monkeypatch.delenv('AGENTS_REGISTRY', raising=False)
        repo = tmp_path / 'consumer'
        _skill(repo, 'api-design', 'canon\n')
        assert main(['--root', str(repo)]) == 0  # source absent -> skip, not fail

    def test_identical_copy_passes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / 'shared-standards'
        repo = tmp_path / 'consumer'
        _skill(src, 'api-design', 'canon body\n')
        _skill(repo, 'api-design', 'canon body\n')
        monkeypatch.setenv('STD_ROOT', str(src))
        assert main(['--root', str(repo)]) == 0

    def test_edited_skill_copy_is_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / 'shared-standards'
        repo = tmp_path / 'consumer'
        _skill(src, 'api-design', 'canon body\n')
        _skill(repo, 'api-design', 'canon body\nHAND EDIT\n')
        monkeypatch.setenv('STD_ROOT', str(src))
        assert main(['--root', str(repo)]) == 1

    def test_extra_file_in_copy_is_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / 'shared-standards'
        repo = tmp_path / 'consumer'
        _skill(src, 'api-design', 'canon\n')
        _skill(repo, 'api-design', 'canon\n')
        (repo / '.claude' / 'skills' / 'api-design' / 'extra.md').write_text('x', encoding='utf-8')
        monkeypatch.setenv('STD_ROOT', str(src))
        assert main(['--root', str(repo)]) == 1

    def test_repo_local_skill_ignored(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / 'shared-standards'
        repo = tmp_path / 'consumer'
        _skill(src, 'api-design', 'canon\n')
        _skill(repo, 'api-design', 'canon\n')
        _skill(repo, 'repo-only', 'not managed\n')  # absent from source -> not compared
        monkeypatch.setenv('STD_ROOT', str(src))
        assert main(['--root', str(repo)]) == 0

    def test_edited_agent_copy_is_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        reg = tmp_path / 'agent-config'
        repo = tmp_path / 'consumer'
        _agent(reg, 'general-qa', 'registry agent\n')
        _agent(repo, 'general-qa', 'registry agent\nEDIT\n')
        monkeypatch.setenv('AGENTS_REGISTRY', str(reg))
        assert main(['--root', str(repo)]) == 1

    def test_source_repo_self_compare_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / 'shared-standards'
        _skill(src, 'api-design', 'canon\n')
        monkeypatch.setenv('STD_ROOT', str(src))
        assert main(['--root', str(src)]) == 0  # repo IS the source -> nothing to diff
