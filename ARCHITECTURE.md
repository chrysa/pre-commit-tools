# Architecture — pre-commit-tools

## Purpose

`pre_commit_hooks_tools` is a collection of pre-commit hooks for chrysa projects
(distributed under the PyPI name `pre-commit-hooks-tools`, package version
`0.0.34`, MIT). It bundles ~80 small static-analysis / linting / formatting hooks
covering Python, TypeScript/React, CSS, Docker/Compose, YAML/JSON, Django/FastAPI,
Claude agent & skill assets, security (secrets, PII, CORS), plus quality gates and
a screenshot capture/publish workflow. Consumers reference it via a standard
`.pre-commit-hooks.yaml` (81 hook ids declared).

## Stack

- **Language:** Python, `requires-python = ">=3.14"` (README badges say 3.14+).
- **Build backend:** setuptools (`setuptools>=72`, `wheel`) via `pyproject.toml`.
- **Key runtime deps (extras):** `tree-sitter` + `tree-sitter-typescript` (TS
  parsing), `requests` (screenshot extra), `chrysa-quality-gate` (git+ssh
  dependency, in `dev` extra). Optional extras: `dead_code`, `format_dockerfile`,
  `lint` (ruff==0.16.3), `screenshot`, `test`, `ts_unreachable_code`, `typecheck`,
  `yaml`.
- **Tooling:** ruff (lint), mypy (type-check), pytest + coverage (`--cov-fail-under=85`),
  pylint, bandit, build/twine (publish).

## Layout

- `pre_commit_hooks/` — hook implementations, one module per hook (e.g.
  `print_detection.py`, `ts_no_any.py`, `dockerfile_multi_stage_check.py`,
  `cors_allow_all.py`, `pii_in_logs.py`, `adr_gate.py`, `regression_gate.py`).
  Each exposes a `main` entry point wired in `pyproject.toml [project.scripts]`.
  - `pre_commit_hooks/tools/` — shared helpers: `pattern_detection.py`,
    `source_reader.py`, `frontmatter.py`, `pre_commit_tools.py`, `logger.py`,
    `update_readme.py`.
  - `pre_commit_hooks/screenshot_sync/` — screenshot capture/publish support
    (`capture/`, `publish/`, `config.py`, `manifest.py`, `gitutil.py`,
    `reporting.py`); driven by `screenshot_capture.py` / `screenshot_publish.py`.
- `scripts/` — `gen_context_files.py`, `quality_gate.py` (standalone larger tools).
- `config-tools/` — bundled linter configs shipped for consumers (`.csslintrc`,
  `.hadolint.yaml`, `.markdownlint.yaml`, `.yamllint.yaml`, `bandit.yaml`,
  `black.toml`, quality-gate Makefiles).
- `makefiles/` — reusable Makefile fragments.
- `standards/`, `docs/` — conventions and reference documentation.
- `tests/` — pytest suite.
- Root config: `.pre-commit-hooks.yaml`, `.pre-commit-config.yaml`, `Makefile`,
  `Dockerfile.test`, `cliff.toml`, `sonar-project.properties`, `.quality-gate*.json`.

## Entrypoints

- **Console scripts** (declared in `pyproject.toml [project.scripts]`, invoked by
  pre-commit): ~80 `<hook-name> = pre_commit_hooks.<module>:main`, e.g.
  `no-sync-in-async`, `ts-no-any`, `claude-agent-frontmatter`, `claude-mcp-config`,
  `no-create-all`, `screenshot-capture`, `screenshot-publish`.
- **Hook manifest:** `.pre-commit-hooks.yaml` (81 `- id:` entries) is the public
  contract consumers reference.
- **Standalone scripts:** `scripts/quality_gate.py`, `scripts/gen_context_files.py`.

## Data / External deps

- No database. Operates on files passed by pre-commit.
- `chrysa-quality-gate` pulled over `git+ssh` from `github.com/chrysa/chrysa-lib`
  (dev/quality-gate use).
- Screenshot extra uses `requests` (network) for capture/publish.
- No secrets committed in source read (repo carries `.gitleaks.toml`,
  `.secrets.baseline`, and secret/PII-detection hooks).

## Build & test (real commands)

```bash
make install          # pip install -e ".[format_dockerfile,yaml]"
make install-dev      # editable install + dev extras (lint, type-check, test, build)
make install-pre-commit
make lint             # ruff check <package>
make typecheck        # mypy
make test             # pytest
make test-cov         # pytest with coverage
make ci               # lint + typecheck + test
make build            # clean + build sdist/wheel
make pre-commit       # pre-commit run --all-files --verbose
docker build -f Dockerfile.test -t pre-commit-tools-test . && docker run --rm pre-commit-tools-test  # make test-docker
```

Note: `pyproject.toml` sets `requires-python = ">=3.14"`; the README states the
same (Python 3.14+).
