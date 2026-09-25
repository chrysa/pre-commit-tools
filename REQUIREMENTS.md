# Requirements — pre-commit-tools

> Reverse-engineered from source, `pyproject.toml`, `.pre-commit-hooks.yaml`, the
> test suite and CI. Tags: **FACT** (verified in-repo), **INFERENCE** (reasoned
> from evidence), **UNKNOWN** (not determinable from the repo). "IMPLEMENTED" is
> asserted only where a hook module + entry point + test exist.

## Purpose (FACT)

`pre-commit-hooks-tools` is a collection of small, self-contained
[pre-commit](https://pre-commit.com) hooks used across chrysa projects. Each hook
is a Python module exposing a `main(argv) -> int` entry point, wired as a console
script in `pyproject.toml` and published in `.pre-commit-hooks.yaml` for
consumers. Evidence: `pre_commit_hooks/*.py`, `pyproject.toml [project.scripts]`,
`.pre-commit-hooks.yaml`.

## Functional requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| REQ-HOOK-001 | Ship a hook manifest consumers can reference by `repo` + `rev` + hook `id` | IMPLEMENTED (FACT) | `.pre-commit-hooks.yaml` (82 `- id:` entries), README "Using pre-commit-tools with pre-commit" |
| REQ-HOOK-002 | Each published hook has a console-script entry point | IMPLEMENTED (FACT) | `pyproject.toml [project.scripts]` (82 entries), one per manifest id |
| REQ-HOOK-003 | Each hook is independently testable via `main(argv)` returning an exit code (0 pass / non-zero fail) | IMPLEMENTED (FACT) | `tests/test_*.py` (81 files), `main` signature contract in CLAUDE.md |
| REQ-HOOK-004 | Detection hooks report file + line and fail the commit on a match | IMPLEMENTED (INFERENCE) | `tools/pattern_detection.py`, e.g. `print_detection.py`, `no_bare_except.py` |
| REQ-HOOK-005 | Sorter/formatter hooks rewrite files in place and fail when a change was needed | IMPLEMENTED (FACT) | `yaml_sorter.py`, `json_sorter.py`, `makefile_sorter.py`, `requirements_sort.py`, `format_dockerfile.py` and their tests |
| REQ-HOOK-006 | Optional heavy hooks run at the `manual` stage only | IMPLEMENTED (FACT) | README (`python-dead-code`, `generate-changelog` `stages: [manual]`) |
| REQ-HOOK-007 | Provide Claude-asset hooks (skill/agent frontmatter, MCP config, CLAUDE.md facts, drift/assets present) | IMPLEMENTED (FACT) | `claude_skill_frontmatter.py`, `claude_agent_frontmatter.py`, `claude_mcp_config.py`, `claude_md_facts_check.py`, `claude_assets_present.py`, `managed_asset_drift.py` |
| REQ-HOOK-008 | Provide security/PII detection hooks (secrets, CORS, cookies, PII, Sentry PII, localStorage tokens) | IMPLEMENTED (FACT) | `django_hardcoded_secret.py`, `ts_hardcoded_secret.py`, `cors_allow_all.py`, `django_cookie_security.py`, `fastapi_cookie_insecure.py`, `pii_hardcoded.py`, `pii_in_logs.py`, `sentry_no_default_pii.py`, `react_token_localstorage.py` |
| REQ-HOOK-009 | Provide governance gates (ADR gate, docs-drift gate, regression/quality gate, dependabot classification) | IMPLEMENTED (FACT) | `adr_gate.py`, `docs_drift_gate.py`, `regression_gate.py`, `scripts/quality_gate.py`, `dependabot_classified_deps.py` |
| REQ-HOOK-010 | Provide a screenshot capture/publish workflow | IMPLEMENTED (FACT) | `screenshot_capture.py`, `screenshot_publish.py`, `pre_commit_hooks/screenshot_sync/` |
| REQ-HOOK-011 | Auto-generate the README hooks table/TOC from the manifest | IMPLEMENTED (FACT) | `pre_commit_hooks/tools/update_readme.py`, README `<!--TOC-->` markers |
| REQ-HOOK-012 | Generate repo context files (handover, ai-instructions) | IMPLEMENTED (FACT) | `scripts/gen_context_files.py`; generated `handover.md`, `ai-instructions.md` headers |

## Non-functional requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| REQ-NFR-001 | Python >= 3.14 | ENFORCED (FACT) | `pyproject.toml requires-python = ">=3.14"`, `Dockerfile.test FROM python:3.14-slim` |
| REQ-NFR-002 | Test coverage stays >= 85% | ENFORCED (FACT) | `pyproject.toml addopts = "... --cov-fail-under=85"` |
| REQ-NFR-003 | Lint (ruff) with zero tolerance; every `# noqa` carries a rule code + reason | ENFORCED (FACT) | `pyproject.toml [tool.ruff]`, CLAUDE.md "Ruff — zero tolerance" |
| REQ-NFR-004 | Static typing enforced via mypy (strict-leaning flags) | ENFORCED (FACT) | `pyproject.toml [tool.mypy]` (`warn_unreachable`, `warn_unused_ignores`, …) |
| REQ-NFR-005 | Pylint fail-under threshold | ENFORCED (FACT) | `pyproject.toml` pylint `fail-under = 9` |
| REQ-NFR-006 | English-only across code, comments, docs, config | POLICY (FACT) | CLAUDE.md "Language Rules"; enforced socially + `hookify.warn-french-in-files.local.md` |
| REQ-NFR-007 | Hooks depend only on files pre-commit passes; no database | FACT | ARCHITECTURE.md "Data / External deps"; no DB code in tree |
| REQ-NFR-008 | Tests runnable in a container matching CI | IMPLEMENTED (FACT) | `Dockerfile.test`, `make docker-test` |

## Out of scope / non-goals (INFERENCE)

- No runtime service, HTTP API, or persistent storage — this is a lint-tool library.
- Not a general-purpose linter replacement; hooks are chrysa-opinionated.
- No frontend/UI surface (the screenshot workflow captures *other* projects' UIs).

## Key UNKNOWNs

- PyPI publish cadence and whether every version is released (release is manual/CI-gated). UNKNOWN.
- Which downstream repos pin which `rev`. UNKNOWN from this repo.
