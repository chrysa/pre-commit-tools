"""Tests for the claude_agent_frontmatter hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.claude_agent_frontmatter import check_agent, main

VALID = '\n'.join(
    (
        '---',
        'name: code-reviewer',
        'description: Use to review a diff for correctness and security issues.',
        'tools: Read, Grep, Glob',
        'model: sonnet',
        '---',
        '',
        'You are a senior code reviewer.',
    ),
)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Create ``<tmp_path>/<name>`` with *content* and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    return path


class TestCheckAgent:
    """Behaviour of check_agent on a single agent definition."""

    def test_valid_agent_has_no_findings(self, tmp_path: Path) -> None:
        errors, warnings = check_agent(_write(tmp_path, 'code-reviewer.md', VALID))
        assert errors == []
        assert warnings == []

    def test_missing_front_matter_is_an_error(self, tmp_path: Path) -> None:
        errors, _ = check_agent(_write(tmp_path, 'code-reviewer.md', 'You are a reviewer.\n'))
        assert errors == ['no YAML front matter: the subagent is never registered']

    def test_name_mismatching_file_stem_is_an_error(self, tmp_path: Path) -> None:
        errors, _ = check_agent(_write(tmp_path, 'reviewer.md', VALID))
        assert errors == ['`name: code-reviewer` must match the file name `reviewer.md`']

    def test_non_kebab_case_name_is_an_error(self, tmp_path: Path) -> None:
        content = VALID.replace('name: code-reviewer', 'name: CodeReviewer')
        errors, _ = check_agent(_write(tmp_path, 'CodeReviewer.md', content))
        assert any('kebab-case' in error for error in errors)

    def test_missing_description_is_an_error(self, tmp_path: Path) -> None:
        content = '\n'.join(('---', 'name: code-reviewer', '---', '', 'Prompt.'))
        errors, _ = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert errors == ['missing required front matter key `description`']

    def test_empty_body_is_an_error(self, tmp_path: Path) -> None:
        content = '\n'.join(
            ('---', 'name: code-reviewer', 'description: Reviews diffs for issues.', '---', '', '   ', ''),
        )
        errors, _ = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert errors == ['empty body: the subagent has no system prompt']

    def test_tools_as_list_is_accepted(self, tmp_path: Path) -> None:
        content = VALID.replace('tools: Read, Grep, Glob', 'tools: [Read, Grep]')
        errors, _ = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert errors == []

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ('tools: 42', '`tools` must be a comma-separated string or a list of tool names'),
            ('tools: ""', '`tools` is empty: omit the key to inherit every tool'),
            ('tools: []', '`tools` is an empty list: omit the key to inherit every tool'),
            ('tools: [Read, 42]', '`tools` list entries must be non-empty tool names'),
        ],
    )
    def test_malformed_tools_is_an_error(self, tmp_path: Path, value: str, expected: str) -> None:
        content = VALID.replace('tools: Read, Grep, Glob', value)
        errors, _ = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert errors == [expected]

    @pytest.mark.parametrize('model', ['opus', 'haiku', 'inherit', 'claude-opus-5'])
    def test_known_model_has_no_warning(self, tmp_path: Path, model: str) -> None:
        content = VALID.replace('model: sonnet', f'model: {model}')
        _, warnings = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert warnings == []

    def test_unknown_model_is_a_warning(self, tmp_path: Path) -> None:
        content = VALID.replace('model: sonnet', 'model: gpt-4')
        errors, warnings = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert errors == []
        assert any('neither a known alias' in warning for warning in warnings)

    def test_non_string_model_is_a_warning(self, tmp_path: Path) -> None:
        content = VALID.replace('model: sonnet', 'model: 5')
        _, warnings = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert warnings == ['`model` must be a model alias or id string']

    def test_unknown_key_is_a_warning(self, tmp_path: Path) -> None:
        content = VALID.replace('model: sonnet', 'model: sonnet\ntemperature: 0.2')
        errors, warnings = check_agent(_write(tmp_path, 'code-reviewer.md', content))
        assert errors == []
        assert warnings == ['unknown front matter key `temperature` (ignored by Claude Code)']

    def test_allowed_extra_key_is_not_warned(self, tmp_path: Path) -> None:
        content = VALID.replace('model: sonnet', 'model: sonnet\ntemperature: 0.2')
        path = _write(tmp_path, 'code-reviewer.md', content)
        _, warnings = check_agent(path, extra_keys=frozenset({'temperature'}))
        assert warnings == []


class TestClaudeAgentFrontmatterMain:
    """Behaviour of the hook entry point."""

    def test_valid_agent_returns_zero(self, tmp_path: Path) -> None:
        assert main([str(_write(tmp_path, 'code-reviewer.md', VALID))]) == 0

    def test_invalid_agent_returns_one(self, tmp_path: Path) -> None:
        assert main([str(_write(tmp_path, 'code-reviewer.md', 'Prompt only.\n'))]) == 1

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'absent.md')]) == 0

    def test_no_arguments_returns_zero(self) -> None:
        assert main([]) == 0

    def test_error_is_reported_on_stderr(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = _write(tmp_path, 'code-reviewer.md', 'Prompt only.\n')
        assert main([str(path)]) == 1
        assert 'error: no YAML front matter' in capsys.readouterr().err

    def test_allow_key_silences_the_warning(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        content = VALID.replace('model: sonnet', 'model: sonnet\ntemperature: 0.2')
        path = _write(tmp_path, 'code-reviewer.md', content)
        assert main([str(path), '--allow-key', 'temperature']) == 0
        assert capsys.readouterr().err == ''
