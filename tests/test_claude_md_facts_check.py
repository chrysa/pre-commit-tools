#!/usr/bin/python3
"""Tests for the claude-md-facts-check hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.claude_md_facts_check import (
    check_make_targets,
    check_project_name,
    check_python_version,
    check_stack_claim,
    collect_findings,
    main,
    resolve_repo_root,
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding='utf-8')
    return path


class TestResolveRepoRoot:
    def test_doc_beside_repo(self, tmp_path: Path) -> None:
        doc = _write(tmp_path / 'CLAUDE.md', '# doc')
        assert resolve_repo_root(doc) == tmp_path.resolve()

    def test_doc_under_dot_claude(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        doc = _write(claude_dir / 'CLAUDE.md', '# doc')
        assert resolve_repo_root(doc) == tmp_path.resolve()


class TestCheckStackClaim:
    def test_python_claim_without_manifest_or_sources_fails(self, tmp_path: Path) -> None:
        finding = check_stack_claim('This is a Python project.', tmp_path)
        assert finding is not None
        assert 'Python' in finding.message
        assert not finding.warn

    def test_python_claim_with_manifest_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "x"\n')
        assert check_stack_claim('A Python / FastAPI service.', tmp_path) is None

    def test_python_claim_with_sources_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'app.py', 'x = 1\n')
        assert check_stack_claim('Django lives here.', tmp_path) is None

    def test_no_stack_keyword_is_skipped(self, tmp_path: Path) -> None:
        assert check_stack_claim('A repository of prose.', tmp_path) is None

    def test_js_claim_with_package_json_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'package.json', '{"name": "x"}')
        assert check_stack_claim('A TypeScript / React app.', tmp_path) is None


class TestCheckPythonVersion:
    def test_disagreeing_minor_fails(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', 'requires-python = ">=3.14"\n')
        finding = check_python_version('Runs on Python 3.11 here.', tmp_path)
        assert finding is not None
        assert '3.11' in finding.message
        assert '3.14' in finding.message

    def test_agreeing_minor_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', 'requires-python = ">=3.14"\n')
        assert check_python_version('Python 3.14 only.', tmp_path) is None

    def test_no_pyproject_is_skipped(self, tmp_path: Path) -> None:
        assert check_python_version('Python 3.11.', tmp_path) is None

    def test_no_version_in_doc_is_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', 'requires-python = ">=3.14"\n')
        assert check_python_version('No version stated.', tmp_path) is None


class TestCheckMakeTargets:
    def test_missing_target_fails(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        findings = check_make_targets('Run `make lint` to check.', tmp_path)
        assert len(findings) == 1
        assert 'make lint' in findings[0].message

    def test_existing_target_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        assert check_make_targets('Run `make test` first.', tmp_path) == []

    def test_target_in_included_mk_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'include makefiles/*.mk\n')
        makefiles = tmp_path / 'makefiles'
        makefiles.mkdir()
        _write(makefiles / 'ci.mk', 'deploy:\n\techo go\n')
        assert check_make_targets('Then `make deploy`.', tmp_path) == []

    def test_no_makefile_is_skipped(self, tmp_path: Path) -> None:
        assert check_make_targets('Run `make lint`.', tmp_path) == []

    def test_target_in_dot_makefile_fragment_passes(self, tmp_path: Path) -> None:
        # chrysa Makefiles include `*.Makefile` fragments via a shell/wildcard glob.
        _write(tmp_path / 'Makefile', 'include $(wildcard *.Makefile)\n')
        _write(tmp_path / 'tools.Makefile', 'pre-commit-run:\n\techo hi\n')
        assert check_make_targets('Run `make pre-commit-run`.', tmp_path) == []

    def test_target_in_nested_makefile_fragment_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'include $(shell find . -name "*.Makefile")\n')
        sub = tmp_path / 'lib' / 'python'
        sub.mkdir(parents=True)
        _write(sub / 'quality.Makefile', 'typecheck:\n\tmypy\n')
        assert check_make_targets('Run `make typecheck`.', tmp_path) == []

    def test_duplicate_reference_reported_once(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        findings = check_make_targets('`make lint` and again `make lint`.', tmp_path)
        assert len(findings) == 1

    def test_bare_prose_make_is_not_a_target(self, tmp_path: Path) -> None:
        # English prose must never be mistaken for a make target: only
        # code-spanned `make <target>` counts.
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        text = 'Please make sure to run make targets and make it green.'
        assert check_make_targets(text, tmp_path) == []

    def test_negated_counterexample_is_not_flagged(self, tmp_path: Path) -> None:
        # A make target named only to say it is WRONG must not be reported.
        _write(tmp_path / 'Makefile', 'typecheck:\n\tmypy\n')
        text = 'Use `make typecheck`, never `make type-check`.'
        assert check_make_targets(text, tmp_path) == []

    def test_negated_line_with_correct_target_named(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'typecheck:\n\tmypy\n')
        text = 'the Makefile (no `make type-check` when the target is `typecheck`).'
        assert check_make_targets(text, tmp_path) == []

    def test_real_missing_target_still_flagged_despite_negation_elsewhere(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        text = 'Never `make type-check`.\nRun `make deploy` to ship.'
        findings = check_make_targets(text, tmp_path)
        assert len(findings) == 1
        assert 'make deploy' in findings[0].message


class TestCheckProjectName:
    def test_name_drift_warns(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "real_name"\n')
        finding = check_project_name('The `other_name` package.', tmp_path)
        assert finding is not None
        assert finding.warn
        assert 'real_name' in finding.message

    def test_matching_name_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "real_name"\n')
        assert check_project_name('Install `real_name` now.', tmp_path) is None

    def test_no_code_spans_is_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "real_name"\n')
        assert check_project_name('Plain prose, no spans.', tmp_path) is None

    def test_no_manifest_is_skipped(self, tmp_path: Path) -> None:
        assert check_project_name('The `whatever` package.', tmp_path) is None

    def test_package_json_name(self, tmp_path: Path) -> None:
        _write(tmp_path / 'package.json', '{"name": "real-js"}')
        finding = check_project_name('The `wrong-js` app.', tmp_path)
        assert finding is not None
        assert 'real-js' in finding.message


class TestCollectFindings:
    def test_clean_doc_has_no_findings(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "x"\nrequires-python = ">=3.14"\n')
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        text = 'Python 3.14 project `x`. Run `make test`.'
        assert collect_findings(tmp_path / 'CLAUDE.md', text, tmp_path) == []


class TestMain:
    def test_clean_doc_returns_0(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "x"\nrequires-python = ">=3.14"\n')
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        doc = _write(tmp_path / 'CLAUDE.md', 'Python 3.14 project `x`. Run `make test`.')
        assert main([str(doc)]) == 0

    def test_bad_make_target_returns_1(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        doc = _write(tmp_path / 'CLAUDE.md', 'Run `make nope`.')
        assert main([str(doc)]) == 1

    def test_name_drift_is_warn_only_by_default(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "real"\n')
        doc = _write(tmp_path / 'CLAUDE.md', 'The `fake` package.')
        assert main([str(doc)]) == 0

    def test_name_drift_fails_under_strict(self, tmp_path: Path) -> None:
        _write(tmp_path / 'pyproject.toml', '[project]\nname = "real"\n')
        doc = _write(tmp_path / 'CLAUDE.md', 'The `fake` package.')
        assert main([str(doc), '--strict']) == 1

    def test_disable_comment_skips_file(self, tmp_path: Path) -> None:
        _write(tmp_path / 'Makefile', 'test:\n\tpytest\n')
        doc = _write(
            tmp_path / 'CLAUDE.md',
            '<!-- claude-md-facts-check: disable -->\nRun `make nope`.',
        )
        assert main([str(doc)]) == 0

    def test_empty_filenames_returns_0(self) -> None:
        assert main([]) == 0

    def test_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'nope.md')]) == 0
