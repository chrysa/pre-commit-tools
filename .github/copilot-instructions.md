# pre-commit-tools — Copilot Instructions

## MANDATORY: Read Instructions Before Any Task

Before working on hooks, tests, or tooling, read:
- `.github/instructions/hooks.instructions.md` — hook architecture, patterns, entry points
- `.github/instructions/testing.instructions.md` — test conventions, fixtures, parametrize

---

## Project Overview

A collection of [pre-commit](https://pre-commit.com) hooks for code quality checks:
- **Python** hooks: print/pprint/logger/debugger detection, dead code, unreachable code, env checks, JSON/YAML/requirements sort, pylint HTML report, Dockerfile formatting
- **TypeScript/JS** hooks: unreachable code detection (tree-sitter AST)
- **CSS** hooks: duplicate property and duplicate ID detection
- **Security**: pip-audit, detect-secrets

## Architecture

```
pre_commit_hooks/          # hook implementations
    tools/                 # shared utilities
        logger.py          # structured logger
        pattern_detection.py  # base class for pattern-based hooks
        pre_commit_tools.py   # argument parsing helpers
        update_readme.py      # README auto-update utility
tests/                     # pytest tests (one file per hook)
config-tools/              # tool configurations (ruff, bandit, yamllint…)
.pre-commit-hooks.yaml     # hook manifest
setup.cfg                  # entry points + dependencies
```

## Key Constraints

- **Python 3.12+** — use modern type hints (`list[str]`, `str | None`, etc.)
- **Typed** — ALL functions must have full type annotations
- **ruff** — linting via `config-tools/ruff.toml`; run `ruff check --config=config-tools/ruff.toml`
- **pytest** — 100% passing tests required before commit
- **`argv` pattern** — every `main()` must accept `argv: Sequence[str] | None = None` for testability
- **No `shell=True`** without `# noqa: S602` justification
