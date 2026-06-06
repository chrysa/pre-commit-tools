"""Tests for the makefile_check hook."""

from __future__ import annotations

import re
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


class TestRecommendedTargets:
    def test_missing_docker_test_is_warning_not_error(self, tmp_path: Path) -> None:
        # docker-test is recommended for lib, not required: warn, do not fail.
        content = CONFORMANT_LIB.replace(
            'docker-test: ## Docker test\n\tdocker build -f Dockerfile.test -t t . && docker run --rm t\n\n',
            '',
        ).replace(' docker-test', '')
        path = _write(tmp_path, content)
        errors, warnings = check_makefile(path)
        assert not any('missing required targets' in e for e in errors)
        assert any('missing recommended targets' in w and 'docker-test' in w for w in warnings)


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

    def test_legacy_string_in_echo_not_flagged(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace(
            '\t@echo dev',
            '\tdocker compose config && echo "docker-compose config OK"',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('legacy' in e for e in errors)

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

    def test_tool_inside_docker_exec_not_flagged(self, tmp_path: Path) -> None:
        # Paths after a tool run *inside* a container are container-side.
        content = CONFORMANT_LIB.replace(
            'ruff check $(PKG) tests',
            'docker exec $(BACKEND) ruff check app',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('missing path' in e for e in errors)

    def test_tool_inside_docker_compose_run_not_flagged(self, tmp_path: Path) -> None:
        # `pytest` here is a compose *service* name plus a container command.
        content = CONFORMANT_LIB.replace(
            'pytest tests/\n',
            'docker compose run --rm pytest bash -c "pytest /app/tests"\n',
            1,
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('missing path' in e for e in errors)

    def test_pip_install_package_list_not_flagged(self, tmp_path: Path) -> None:
        # Package names after `pip install` are not host paths.
        content = CONFORMANT_LIB.replace(
            'pip install -e ".[dev]"',
            'pip install ruff mypy pytest pytest-cov build twine',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('missing path' in e for e in errors)

    def test_flag_value_not_flagged_as_path(self, tmp_path: Path) -> None:
        # The value of a flag (e.g. --browser chromium) is not a path.
        content = CONFORMANT_LIB.replace(
            'pytest tests/\n',
            'pytest tests/ --browser chromium\n',
            1,
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any("missing path 'chromium'" in e for e in errors)

    def test_inline_shell_comment_not_flagged(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace(
            'mypy $(PKG)',
            'mypy $(PKG) # Run mypy type checking',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any('missing path' in e for e in errors)

    def test_host_run_missing_dir_still_caught(self, tmp_path: Path) -> None:
        # A tool invoked directly on the host must still be path-checked.
        content = CONFORMANT_LIB.replace('mypy $(PKG)', 'mypy genealogy_validator')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any("missing path 'genealogy_validator'" in e for e in errors)

    def test_pipe_to_interpreter_not_flagged(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace(
            'ruff check $(PKG) tests',
            'ruff check $(PKG) | python3 -c "import sys"',
        )
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert not any("missing path 'python3'" in e for e in errors)


class TestPhonyAndHelp:
    def test_no_phony_fails(self, tmp_path: Path) -> None:
        content = '\n'.join(line for line in CONFORMANT_LIB.splitlines() if not line.startswith('.PHONY'))
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any('.PHONY' in e for e in errors)

    def test_shell_computed_phony_not_warned(self, tmp_path: Path) -> None:
        # A `.PHONY: $(shell grep ...)` lists targets dynamically; no warning.
        dynamic = ".PHONY: $(shell grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | cut -d: -f1)"
        content = re.sub(r'^\.PHONY:.*$', dynamic, CONFORMANT_LIB, count=1, flags=re.MULTILINE)
        path = _write(tmp_path, content)
        _, warnings = check_makefile(path)
        assert not any('.PHONY does not list' in w for w in warnings)

    def test_missing_help_fails(self, tmp_path: Path) -> None:
        content = CONFORMANT_LIB.replace(
            "help: ## Show available targets\n\t@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST)\n\n",
            '',
        ).replace('help ', '')
        path = _write(tmp_path, content)
        errors, _ = check_makefile(path)
        assert any("missing 'help'" in e for e in errors)
