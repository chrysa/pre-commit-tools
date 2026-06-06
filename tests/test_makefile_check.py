"""Tests for the makefile_check hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.makefile_check import check_makefile, main

CONFORMANT_LIB = """\
# makefile-tier: lib
.DEFAULT_GOAL := help
PKG := mypkg

.PHONY: help install dev lint format typecheck test test-cov docker-test build clean pre-commit

help: ## Show available targets
\t@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST)

install: ## Install deps
\tpip install -e ".[dev]"

dev: ## Watch
\t@echo dev

lint: ## Lint
\truff check $(PKG) tests

format: ## Format
\truff format $(PKG) tests

typecheck: ## Types
\tmypy $(PKG)

test: ## Test
\tpytest tests/

test-cov: ## Coverage
\tpytest tests/ --cov=$(PKG)

docker-test: ## Docker test
\tdocker build -f Dockerfile.test -t t . && docker run --rm t

build: ## Build
\tpython -m build

clean: ## Clean
\trm -rf build

pre-commit: ## Hooks
\tpre-commit run --all-files
"""


def _write(tmp_path: Path, content: str, *, dirs: tuple[str, ...] = ('mypkg', 'tests')) -> Path:
    for name in dirs:
        (tmp_path / name).mkdir(exist_ok=True)
    path = tmp_path / 'Makefile'
    path.write_text(content, encoding='utf-8')
    return path


class TestConformant:
    def test_lib_passes(self, tmp_path: Path) -> None:
        path = _write(tmp_path, CONFORMANT_LIB)
        errors, _ = check_makefile(path)
        assert errors == []

    def test_main_returns_0(self, tmp_path: Path) -> None:
        path = _write(tmp_path, CONFORMANT_LIB)
        assert main([str(path)]) == 0


class TestTierMarker:
    def test_missing_marker_fails(self, tmp_path: Path) -> None:
        path = _write(tmp_path, CONFORMANT_LIB.replace('# makefile-tier: lib\n', ''))
        errors, _ = check_makefile(path)
        assert any('makefile-tier' in e for e in errors)

    def test_invalid_tier_fails(self, tmp_path: Path) -> None:
        path = _write(tmp_path, CONFORMANT_LIB.replace('lib', 'banana', 1))
        errors, _ = check_makefile(path)
        assert any('invalid tier' in e for e in errors)


class TestRequiredTargets:
    def test_missing_required_target_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace('typecheck: ## Types\n\tmypy $(PKG)\n\n', '')
        content = content.replace(' typecheck', '')  # also drop from .PHONY
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any('missing required targets' in e and 'typecheck' in e for e in errors)


class TestForbiddenNames:
    def test_fmt_target_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace('format: ## Format', 'fmt: ## Format')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any("forbidden target 'fmt'" in e for e in errors)

    def test_type_check_alias_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB + '\ntype-check: typecheck ## alias\n'
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any("forbidden target 'type-check'" in e for e in errors)


class TestDockerCompose:
    def test_legacy_docker_compose_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace('\t@echo dev', '\tdocker-compose up -d')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any('legacy' in e for e in errors)

    def test_glued_typo_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace('\t@echo dev', '\tdocker composelogs -f')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any('glued' in e for e in errors)

    def test_compose_yml_filename_not_flagged(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace(
            '\t@echo dev',
            '\tcat docker-compose.yml',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('legacy' in e for e in errors)


class TestMissingPaths:
    def test_missing_referenced_dir_fails(self, tmp_path: Path) -> None:
        # lint references src/ which is not created
        content = CONFORMANT_LIB.replace('ruff check $(PKG) tests', 'ruff check src tests')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any("missing path 'src'" in e for e in errors)

    def test_existing_dirs_pass(self, tmp_path: Path) -> None:
        path = _write(tmp_path, CONFORMANT_LIB)
        errors, _ = check_makefile(path)
        assert not any('missing path' in e for e in errors)

    def test_tool_name_in_echo_string_not_flagged(self, tmp_path: Path) -> None:
        # A help echo mentioning a tool must not be parsed as a real invocation.
        content = CONFORMANT_LIB.replace(
            '\t@echo dev',
            '\t@echo "  typecheck   Run mypy type checking"',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('missing path' in e for e in errors)

    def test_commented_recipe_line_not_flagged(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace('\t@echo dev', '\t# docker-compose up -d')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('legacy' in e for e in errors)


class TestPhonyAndHelp:
    def test_no_phony_fails(self, tmp_path: Path) -> None:
        content = '\n'.join(line for line in CONFORMANT_LIB.splitlines() if not line.startswith('.PHONY'))
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any('.PHONY' in e for e in errors)

    def test_missing_help_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace(
            "help: ## Show available targets\n\t@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST)\n\n",
            '',
        ).replace('help ', '')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any("missing 'help'" in e for e in errors)
