"""Tests for the claude_skill_frontmatter hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.claude_skill_frontmatter import check_skill, main

VALID = '\n'.join(
    (
        '---',
        'name: my-skill',
        'description: Use when the user asks to validate Claude Code assets in a repository.',
        '---',
        '',
        '# My skill',
        '',
        'Body.',
    ),
)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Create ``<tmp_path>/<name>/SKILL.md`` with *content* and return its path."""
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'SKILL.md'
    path.write_text(content, encoding='utf-8')
    return path


class TestCheckSkill:
    """Behaviour of check_skill on a single SKILL.md."""

    def test_valid_skill_has_no_findings(self, tmp_path: Path) -> None:
        errors, warnings = check_skill(_write(tmp_path, 'my-skill', VALID))
        assert errors == []
        assert warnings == []

    def test_missing_front_matter_is_an_error(self, tmp_path: Path) -> None:
        errors, _ = check_skill(_write(tmp_path, 'my-skill', '# My skill\n\nBody.\n'))
        assert len(errors) == 1
        assert 'invisible to Claude Code' in errors[0]

    def test_legacy_heading_gets_a_migration_hint(self, tmp_path: Path) -> None:
        errors, _ = check_skill(_write(tmp_path, 'my-skill', '# Skill: My Skill\n\nBody.\n'))
        assert "legacy '# Skill:' format detected" in errors[0]

    def test_unclosed_fence_is_an_error(self, tmp_path: Path) -> None:
        content = '\n'.join(('---', 'name: my-skill', 'description: Something long enough here.', ''))
        errors, _ = check_skill(_write(tmp_path, 'my-skill', content))
        assert errors == ['front matter block is never closed by a `---` fence']

    def test_invalid_yaml_is_an_error(self, tmp_path: Path) -> None:
        content = '\n'.join(('---', 'name: [unclosed', '---', '', 'Body.'))
        errors, _ = check_skill(_write(tmp_path, 'my-skill', content))
        assert len(errors) == 1
        assert 'not valid YAML' in errors[0]

    def test_empty_front_matter_is_an_error(self, tmp_path: Path) -> None:
        errors, _ = check_skill(_write(tmp_path, 'my-skill', '---\n---\n\nBody.\n'))
        assert errors == ['front matter block is empty']

    def test_scalar_front_matter_is_an_error(self, tmp_path: Path) -> None:
        errors, _ = check_skill(_write(tmp_path, 'my-skill', '---\njust a string\n---\n\nBody.\n'))
        assert errors == ['front matter must be a YAML mapping']

    def test_missing_description_is_an_error(self, tmp_path: Path) -> None:
        content = '\n'.join(('---', 'name: my-skill', '---', '', 'Body.'))
        errors, _ = check_skill(_write(tmp_path, 'my-skill', content))
        assert errors == ['missing required front matter key `description`']

    def test_blank_description_is_an_error(self, tmp_path: Path) -> None:
        content = '\n'.join(('---', 'name: my-skill', 'description: "   "', '---', '', 'Body.'))
        errors, _ = check_skill(_write(tmp_path, 'my-skill', content))
        assert errors == ['front matter key `description` must be a non-empty string']

    @pytest.mark.parametrize('name', ['My_Skill', 'mySkill', 'my--skill', 'my-skill-'])
    def test_non_kebab_case_name_is_an_error(self, tmp_path: Path, name: str) -> None:
        content = VALID.replace('name: my-skill', f'name: {name}')
        errors, _ = check_skill(_write(tmp_path, name, content))
        assert any('kebab-case' in error for error in errors)

    def test_name_mismatching_directory_is_an_error(self, tmp_path: Path) -> None:
        errors, _ = check_skill(_write(tmp_path, 'other-dir', VALID))
        assert errors == ['`name: my-skill` must match the containing directory `other-dir/`']

    def test_short_description_is_an_error(self, tmp_path: Path) -> None:
        content = VALID.replace(
            'description: Use when the user asks to validate Claude Code assets in a repository.',
            'description: Does stuff.',
        )
        errors, _ = check_skill(_write(tmp_path, 'my-skill', content))
        assert any('too short to act as a trigger' in error for error in errors)

    def test_long_description_is_a_warning(self, tmp_path: Path) -> None:
        content = VALID.replace(
            'description: Use when the user asks to validate Claude Code assets in a repository.',
            f'description: {"x" * 60}',
        )
        errors, warnings = check_skill(_write(tmp_path, 'my-skill', content), max_description=50)
        assert errors == []
        assert any('recommended maximum' in warning for warning in warnings)

    def test_unknown_key_is_a_warning(self, tmp_path: Path) -> None:
        content = VALID.replace('---\n\n# My skill', 'trigger: always\n---\n\n# My skill')
        errors, warnings = check_skill(_write(tmp_path, 'my-skill', content))
        assert errors == []
        assert warnings == ['unknown front matter key `trigger` (ignored by Claude Code)']

    def test_allowed_extra_key_is_not_warned(self, tmp_path: Path) -> None:
        content = VALID.replace('---\n\n# My skill', 'trigger: always\n---\n\n# My skill')
        path = _write(tmp_path, 'my-skill', content)
        _, warnings = check_skill(path, extra_keys=frozenset({'trigger'}))
        assert warnings == []

    def test_argument_hint_is_a_known_key(self, tmp_path: Path) -> None:
        content = VALID.replace('---\n\n# My skill', 'argument-hint: "[path]"\n---\n\n# My skill')
        _, warnings = check_skill(_write(tmp_path, 'my-skill', content))
        assert warnings == []


class TestClaudeSkillFrontmatterMain:
    """Behaviour of the hook entry point."""

    def test_valid_skill_returns_zero(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'my-skill', VALID)
        assert main([str(path)]) == 0

    def test_invalid_skill_returns_one(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'my-skill', '# Skill: legacy\n')
        assert main([str(path)]) == 1

    def test_non_skill_file_is_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / 'README.md'
        path.write_text('# Not a skill\n', encoding='utf-8')
        assert main([str(path)]) == 0

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'absent' / 'SKILL.md')]) == 0

    def test_no_arguments_returns_zero(self) -> None:
        assert main([]) == 0

    def test_warning_only_returns_zero(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        content = VALID.replace('---\n\n# My skill', 'trigger: always\n---\n\n# My skill')
        path = _write(tmp_path, 'my-skill', content)
        assert main([str(path)]) == 0
        assert 'warning: unknown front matter key `trigger`' in capsys.readouterr().err

    def test_allow_key_silences_the_warning(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        content = VALID.replace('---\n\n# My skill', 'trigger: always\n---\n\n# My skill')
        path = _write(tmp_path, 'my-skill', content)
        assert main([str(path), '--allow-key', 'trigger']) == 0
        assert capsys.readouterr().err == ''
