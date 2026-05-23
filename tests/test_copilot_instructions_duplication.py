"""Tests for copilot_instructions_duplication hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.copilot_instructions_duplication import (
    check_duplications,
    extract_sections,
    find_workspace_instructions,
    main,
    similarity,
)

_INSTRUCTIONS_PATH = Path('.github') / 'copilot-instructions.md'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


class TestExtractSections:
    def test_single_section(self) -> None:
        text = '## My Section\n\nSome content here.\n'
        sections = extract_sections(text)
        assert 'My Section' in sections
        assert 'Some content here.' in sections['My Section']

    def test_multiple_sections(self) -> None:
        text = '## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n'
        sections = extract_sections(text)
        assert 'Section A' in sections
        assert 'Section B' in sections

    def test_no_sections(self) -> None:
        text = '# H1 heading\n\nSome text.\n'
        assert extract_sections(text) == {}

    def test_empty_body_section(self) -> None:
        text = '## Empty Section\n\n## Non-empty\n\nContent.\n'
        sections = extract_sections(text)
        assert sections['Empty Section'] == ''
        assert 'Content.' in sections['Non-empty']


class TestSimilarity:
    def test_identical_strings(self) -> None:
        assert similarity('hello', 'hello') == 1.0

    def test_completely_different(self) -> None:
        assert similarity('abc', 'xyz') < 0.5

    def test_partial_overlap(self) -> None:
        ratio = similarity('hello world', 'hello there')
        assert 0.0 < ratio < 1.0


class TestFindWorkspaceInstructions:
    def test_finds_workspace_file_above_repo(self, tmp_path: Path) -> None:
        # Structure: tmp_path/.github/copilot-instructions.md (workspace)
        #            tmp_path/chrysa/my-repo/.github/copilot-instructions.md (repo)
        ws_file = tmp_path / '.github' / 'copilot-instructions.md'
        _write(ws_file, '## Workspace Section\n\nContent.\n')

        repo_file = tmp_path / 'chrysa' / 'my-repo' / '.github' / 'copilot-instructions.md'
        _write(repo_file, '## Repo Section\n\nContent.\n')

        found = find_workspace_instructions(repo_file)
        assert found is not None
        assert found.resolve() == ws_file.resolve()

    def test_returns_none_when_no_workspace_file(self, tmp_path: Path) -> None:
        repo_file = tmp_path / 'chrysa' / 'my-repo' / '.github' / 'copilot-instructions.md'
        _write(repo_file, '## Section\n\nContent.\n')

        found = find_workspace_instructions(repo_file)
        assert found is None

    def test_does_not_return_same_file(self, tmp_path: Path) -> None:
        # Only one instructions file exists — should not return itself
        repo_file = tmp_path / '.github' / 'copilot-instructions.md'
        _write(repo_file, '## Section\n\nContent.\n')

        found = find_workspace_instructions(repo_file)
        assert found is None


class TestCheckDuplications:
    def test_identical_section_flagged(self, tmp_path: Path) -> None:
        body = 'You must automate everything including CI/CD pipelines and linting.\n' * 5
        ws_file = tmp_path / 'ws' / _INSTRUCTIONS_PATH
        _write(ws_file, f'## Automation Rules\n\n{body}')

        repo_file = tmp_path / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, f'## Automation Rules\n\n{body}')

        duplicates = check_duplications(repo_file, ws_file, threshold=0.80)
        assert len(duplicates) == 1
        assert duplicates[0][1] == 'Automation Rules'
        assert duplicates[0][0] >= 0.80

    def test_different_section_not_flagged(self, tmp_path: Path) -> None:
        ws_file = tmp_path / 'ws' / _INSTRUCTIONS_PATH
        _write(ws_file, '## Global Rule\n\nAlways use Docker for builds.\n')

        repo_file = tmp_path / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, '## Repo-Specific Rule\n\nThis project uses PostgreSQL 17.\n')

        duplicates = check_duplications(repo_file, ws_file, threshold=0.80)
        assert duplicates == []

    def test_below_threshold_not_flagged(self, tmp_path: Path) -> None:
        ws_file = tmp_path / 'ws' / _INSTRUCTIONS_PATH
        _write(ws_file, '## CI\n\nRun tests in Docker always.\n')

        repo_file = tmp_path / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, '## CI\n\nUse GitHub Actions for CI.\n')

        duplicates = check_duplications(repo_file, ws_file, threshold=0.95)
        assert duplicates == []

    def test_disable_comment_skips_file(self, tmp_path: Path) -> None:
        body = 'You must automate everything including CI/CD pipelines and linting.\n' * 5
        ws_file = tmp_path / 'ws' / _INSTRUCTIONS_PATH
        _write(ws_file, f'## Automation Rules\n\n{body}')

        repo_file = tmp_path / 'repo' / _INSTRUCTIONS_PATH
        _write(
            repo_file,
            f'<!-- detect-duplicated-copilot-instructions: disable -->\n## Automation Rules\n\n{body}',
        )

        duplicates = check_duplications(repo_file, ws_file, threshold=0.80)
        assert duplicates == []

    def test_empty_body_not_flagged(self, tmp_path: Path) -> None:
        ws_file = tmp_path / 'ws' / _INSTRUCTIONS_PATH
        _write(ws_file, '## Rule\n\nSome content.\n')

        repo_file = tmp_path / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, '## Rule\n\n')

        duplicates = check_duplications(repo_file, ws_file, threshold=0.80)
        assert duplicates == []


class TestMain:
    def test_no_workspace_file_returns_0(self, tmp_path: Path) -> None:
        repo_file = tmp_path / 'chrysa' / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, '## Section\n\nSome unique content here.\n')
        assert main([str(repo_file)]) == 0

    def test_duplicate_section_returns_1(self, tmp_path: Path) -> None:
        body = 'Automate everything: CI, linting, formatting, testing, releases.\n' * 5
        ws_file = tmp_path / _INSTRUCTIONS_PATH
        _write(ws_file, f'## Automation\n\n{body}')

        repo_file = tmp_path / 'chrysa' / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, f'## Automation\n\n{body}')

        assert main([str(repo_file)]) == 1

    def test_unique_section_returns_0(self, tmp_path: Path) -> None:
        ws_file = tmp_path / _INSTRUCTIONS_PATH
        _write(ws_file, '## Global\n\nGlobal engineering rules here.\n')

        repo_file = tmp_path / 'chrysa' / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, '## Project-Specific\n\nThis repo uses a Rust backend.\n')

        assert main([str(repo_file)]) == 0

    def test_custom_threshold_respected(self, tmp_path: Path) -> None:
        # Sections are ~85% similar — should fail at 0.80 but pass at 0.95
        body_ws = 'All tests must run in Docker containers via make targets.\n' * 5
        body_repo = 'All tests must run in Docker containers via Makefile targets.\n' * 5

        ws_file = tmp_path / _INSTRUCTIONS_PATH
        _write(ws_file, f'## Tests\n\n{body_ws}')

        repo_file = tmp_path / 'chrysa' / 'repo' / _INSTRUCTIONS_PATH
        _write(repo_file, f'## Tests\n\n{body_repo}')

        assert main([str(repo_file), '--threshold', '0.95']) == 0

    def test_empty_filenames_returns_0(self) -> None:
        assert main([]) == 0

    def test_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'nonexistent.md')]) == 0
