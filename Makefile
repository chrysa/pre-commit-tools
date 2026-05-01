#!make
ifneq (,)
	$(error This Makefile requires GNU Make)
endif

PYTHON      ?= python3
PIP         ?= pip
PACKAGE_DIR  = pre_commit_hooks

.DEFAULT_GOAL := help

.PHONY: $(shell grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | cut -d":" -f1 | tr "\n" " ")

help: ## Display this help message
	@echo "==================================================================="
	@echo "pre-commit-tools Development Environment"
	@echo "==================================================================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@for makefile in $(shell echo $(MAKEFILE_LIST) | sort); do \
		grep -E '^[a-zA-Z_-]+(\([^)]*\))?:.*?## .*$$' $$makefile 2>/dev/null | sort | \
			awk 'BEGIN {FS = ":.*?## "}; { \
				cmd = $$1; \
				desc = $$2; \
				if (match(cmd, /\([^)]+\)/)) { \
					args = substr(cmd, RSTART+1, RLENGTH-2); \
					gsub(/\([^)]+\)/, "", cmd); \
					printf "  \033[36m%-25s\033[0m \033[33m%-15s\033[0m %s\n", cmd, args, desc; \
				} else { \
					printf "  \033[36m%-25s\033[0m \033[33m%-15s\033[0m %s\n", cmd, "", desc; \
				} \
			}'; \
		echo ""; \
	done
	@echo "==================================================================="

# ── Installation ────────────────────────────────────────────────────────────

install: ## Install package with all extras
	$(PIP) install -e ".[format_dockerfile,yaml]"

install-dev: ## Install package + dev dependencies (lint, type-check, test, build)
	$(PIP) install -e ".[format_dockerfile,yaml,dead_code]"
	$(PIP) install ruff mypy pylint pytest pytest-cov build twine

install-pre-commit: ## Install and configure git pre-commit hooks
	$(PIP) install --quiet pre-commit
	pre-commit install
	pre-commit autoupdate

# ── Quality ──────────────────────────────────────────────────────────────────

lint: ## Run ruff linting
	ruff check --config=config-tools/ruff.toml $(PACKAGE_DIR)

format: ## Run ruff formatter
	ruff format --config=config-tools/ruff.toml $(PACKAGE_DIR)

format-check: ## Check ruff formatting (no changes)
	ruff format --check --config=config-tools/ruff.toml $(PACKAGE_DIR)

type-check: ## Run mypy type checking
	mypy --config-file=setup.cfg $(PACKAGE_DIR)

pylint: ## Run pylint static analysis
	pylint --rcfile=setup.cfg --reports=no --score=no --persistent=no $(PACKAGE_DIR)

quality: lint format-check type-check ## Run lint + format-check + type-check

pre-commit: ## Run all pre-commit hooks on every file
	pre-commit run --all-files --verbose

pre-commit-manual: ## Run manual-stage pre-commit hooks on every file
	pre-commit run --all-files --hook-stage manual

# ── Tests ────────────────────────────────────────────────────────────────────

test: ## Run test suite
	pytest

test-cov: ## Run test suite with coverage report
	pytest --cov=$(PACKAGE_DIR) --cov-branch \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage_html_report

test-fail-fast: ## Run tests and stop on first failure
	pytest --failed-first --showlocals -x

test-debug: ## Run tests and launch pdb on first failure
	pytest --failed-first --pdb

# ── Build & Release ──────────────────────────────────────────────────────────

clean: ## Remove all build / cache artefacts
	@rm -rf *.egg-info build/ dist/ reports/ .mypy_cache .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean ## Build source and wheel distribution packages
	$(PYTHON) -m build

publish: build ## Upload distribution to PyPI
	$(PYTHON) -m twine upload dist/*

publish-test: build ## Upload distribution to TestPyPI
	$(PYTHON) -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# ── Quality Gates ──────────────────────────────────────────────────────────────

quality-gate-baseline: ## Record baseline metrics for regression detection
	@python3 scripts/quality_gate.py baseline

quality-gate-verify: ## Verify no regression since baseline
	@python3 scripts/quality_gate.py verify
