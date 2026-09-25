# Constraints — pre-commit-tools

Tags: **FACT** (verified in-repo), **INFERENCE**, **UNKNOWN**.

## Platform & runtime

- **CON-001 (FACT)** — Python **>= 3.14**. `pyproject.toml requires-python = ">=3.14"`;
  `Dockerfile.test` uses `python:3.14-slim`. Consumers on older interpreters cannot
  install the package directly.
- **CON-002 (FACT)** — Build backend is **setuptools** (`setuptools>=72`, `wheel`),
  not hatch/poetry. `pyproject.toml [build-system]`.
- **CON-003 (FACT)** — Optional functionality is gated behind **extras**; a hook may
  fail if its extra is not installed. Per-hook mapping in CLAUDE.md "Optional extras
  required per hook" and README.

## Toolchain gates (must pass)

- **CON-004 (FACT)** — **ruff** lint + format, zero warnings. `[tool.ruff]`.
- **CON-005 (FACT)** — **mypy** type-check with warn-on-* flags. `[tool.mypy]`.
- **CON-006 (FACT)** — **pytest** coverage `--cov-fail-under=85`. `[tool.pytest]`.
- **CON-007 (FACT)** — **pylint** `fail-under = 9`. `[tool.pylint]`.
- **CON-008 (FACT)** — All local checks go through **`make` targets**; invoking
  `ruff`/`pytest`/`mypy` directly on the host is disallowed by convention.
  CLAUDE.md "Local test procedure"; reinforced by `.claude/hookify.warn-host-test-lint.local.md`.

## Coding conventions (non-negotiable per CLAUDE.md — FACT)

- **CON-009** — `from __future__ import annotations` at the top of every module.
- **CON-010** — PEP 585/604 builtins generics (`list[str]`, `str | None`); never
  `List`/`Optional`/`Union`.
- **CON-011** — Mandatory entry-point signature `def main(argv: Sequence[str] | None = None) -> int`.
- **CON-012** — Use `tools/pre_commit_tools.py` (`PreCommitTools`) instead of inline `argparse`.
- **CON-013** — `Path.read_text(encoding="utf-8")`, never bare `open()`.
- **CON-014** — English only in all code, comments, docs, config.

## Dependency / supply-chain

- **CON-015 (FACT)** — Dev/quality-gate depends on **`chrysa-quality-gate`** pulled
  over `git+ssh` from `github.com/chrysa/chrysa-lib` — requires SSH access to that
  private repo to install the `dev` extra. `pyproject.toml`.
- **CON-016 (FACT)** — `ruff` pin (`ruff==0.16.3`) must stay in sync with the
  `ruff-pre-commit` rev used downstream. `pyproject.toml lint` extra comment.
- **CON-017 (FACT / known upstream bug)** — ruff target kept at **py313** (not py314)
  because `ruff format <=0.15.15` strips multi-except parens under py314.
  `pyproject.toml [tool.ruff]` comment.

## Process / repo

- **CON-018 (FACT)** — Pushing to `chrysa/pre-commit-tools` requires the **`chrysa`
  GitHub account** (`gh auth switch --user chrysa` + token injection). CLAUDE.md
  "Known pitfalls". `anthony-greau` is pull-only (global memory).
- **CON-019 (FACT)** — `main` is production, `develop` is the workspace; merges are
  PR-gated by branch protection (`gh pr merge <n> --admin` when blocked). CLAUDE.md;
  chrysa SCM standards.
- **CON-020 (FACT)** — Before `pre-commit run`, `pip install -e .` is REQUIRED so the
  console-script entry points resolve. CLAUDE.md "Known pitfalls".
- **CON-021 (INFERENCE)** — `.venv/`, `dist/`, cache dirs, and large vendored blobs
  (`graphify` 11.5M, `sys` 34.5M) exist in the working tree but are build/tool
  artefacts, not sources. Their tracked status is UNKNOWN (not verified against
  `.gitignore` here).

## Contradictions to resolve (see REVIEW.md)

- **CON-022** — CLAUDE.md and README describe a **Python 3.12/3.13/3.14 matrix**, but
  `pyproject.toml requires-python`, `Dockerfile.test`, and `ci.yml` all target
  **3.14 only**. The matrix claim appears stale.
