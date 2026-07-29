"""Tests for claude_assets_present."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.claude_assets_present import main

MANAGED = '<!-- chrysa:standards:start -->\n# chrysa — Transverse Standards\n'


def _fleet_repo(tmp_path: Path, *, with_skills: bool) -> Path:
    (tmp_path / 'CLAUDE.md').write_text(MANAGED, encoding='utf-8')
    if with_skills:
        skill = tmp_path / '.claude' / 'skills' / 'testing-pytest'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: testing-pytest\n---\n', encoding='utf-8')
    return tmp_path


class TestClaudeAssetsPresent:
    def test_fleet_repo_without_skills_is_flagged(self, tmp_path: Path) -> None:
        _fleet_repo(tmp_path, with_skills=False)
        assert main(['--root', str(tmp_path)]) == 1

    def test_fleet_repo_with_skills_is_ok(self, tmp_path: Path) -> None:
        _fleet_repo(tmp_path, with_skills=True)
        assert main(['--root', str(tmp_path)]) == 0

    def test_empty_skills_dir_is_flagged(self, tmp_path: Path) -> None:
        _fleet_repo(tmp_path, with_skills=False)
        (tmp_path / '.claude' / 'skills').mkdir(parents=True)
        assert main(['--root', str(tmp_path)]) == 1

    def test_skill_dir_without_skill_md_is_flagged(self, tmp_path: Path) -> None:
        _fleet_repo(tmp_path, with_skills=False)
        (tmp_path / '.claude' / 'skills' / 'broken').mkdir(parents=True)
        assert main(['--root', str(tmp_path)]) == 1

    def test_non_fleet_repo_is_skipped(self, tmp_path: Path) -> None:
        (tmp_path / 'CLAUDE.md').write_text('# local notes, no managed block\n', encoding='utf-8')
        assert main(['--root', str(tmp_path)]) == 0

    def test_repo_without_claude_md_is_skipped(self, tmp_path: Path) -> None:
        assert main(['--root', str(tmp_path)]) == 0

    def test_filenames_are_ignored(self, tmp_path: Path) -> None:
        _fleet_repo(tmp_path, with_skills=True)
        assert main(['some/file.py', '--root', str(tmp_path)]) == 0
