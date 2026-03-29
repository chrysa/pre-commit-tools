# pre-commit-tools — Copilot Instructions

## MANDATORY: Read Instructions Before Any Task

Before working on hooks, tests, or tooling, read **all** relevant instruction files:

| File | Applies to |
|---|---|
| `.github/instructions/hooks.instructions.md` | `pre_commit_hooks/**/*.py` — hook architecture, entry points, patterns |
| `.github/instructions/python_guidelines.instructions.md` | `**/*.py` — Python 3.12+, typing, error handling |
| `.github/instructions/typing.instructions.md` | `**/*.py` — PEP 585/604, no Any, return annotations |
| `.github/instructions/ruff_compliance.instructions.md` | `**/*.py` — ruff rules, zero-tolerance policy |
| `.github/instructions/testing.instructions.md` | `tests/**/*.py` — test conventions, `_write()`, \n strings |
| `.github/instructions/frontend_guidelines.instructions.md` | `**/*.{ts,tsx,js,jsx,css}` — components, props, no console |

---

## Project Overview

A collection of [pre-commit](https://pre-commit.com) hooks for code quality checks:

- **Python** hooks: print/pprint/logger/debugger detection, dead code, unreachable code, env checks, JSON/YAML/requirements sort, pylint HTML report, Dockerfile formatting
- **TypeScript/JS** hooks: unreachable code detection (tree-sitter AST), console.* detection, prop-types, direct DOM manipulation
- **CSS** hooks: duplicate property, duplicate ID, unused variable detection
- **Django/FastAPI** hooks: hardcoded secrets, no raw SQL, debug settings, migration print, sync-in-async, missing response_model
- **Security**: no-bare-except, dockerfile-no-latest, env-example-sync
- **Config centralisation**: YAML/JSON/requirements sorters, Dockerfile formatter

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
.github/instructions/      # Copilot instruction files (READ BEFORE CODING)
.pre-commit-hooks.yaml     # hook manifest
setup.cfg                  # entry points + dependencies
```

## Key Constraints

- **Python 3.12+** (target 3.14, retro-compatible 3.12) — use `list[str]`, `str | None`, etc.
- **Typed** — ALL public functions must have complete type annotations (Ruff ANN)
- **ruff** — zero-tolerance linting via `config-tools/ruff.toml`
- **pytest** — 100% passing tests required before commit
- **`argv` pattern** — every `main()` must accept `argv: Sequence[str] | None = None`
- **No `shell=True`** without `# noqa: S602` justification
- **`from __future__ import annotations`** — in every Python file

## Available Hooks (complete list)

### JavaScript / TypeScript
| Hook ID | Purpose |
|---|---|
| `console-debug-detection` | `console.debug()` in .js/.gs files |
| `console-log-detection` | `console.log()` |
| `console-table-detection` | `console.table()` |
| `react-console-error-detection` | `console.error()` in .tsx/.jsx |
| `no-console-warn` | `console.warn()` |
| `ts-unreachable-code-detection` | Dead code after return/throw/break/continue in .ts/.tsx/.js/.jsx |
| `react-direct-dom` | document.getElementById etc. in React files |
| `import-no-relative-parent` | Deep relative imports (../../) |

### CSS
| Hook ID | Purpose |
|---|---|
| `css-duplicate-property-detection` | Duplicate CSS properties + duplicate IDs |
| `css-unused-variable-detection` | Declared --var unused |

### Python
| Hook ID | Purpose |
|---|---|
| `python-print-detection` | print() |
| `python-pprint-detection` | pprint() |
| `debugger-detection` | breakpoint/pdb/ipdb |
| `logger-detection` | logging.* direct calls |
| `python-unreachable-code` | Dead code after return/raise/break/continue |
| `python-dead-code` | Implicit unused code (vulture) |
| `no-bare-except-detection` | bare `except:` clauses |

### Django / FastAPI
| Hook ID | Purpose |
|---|---|
| `no-print-in-migration` | print() in Django migrations |
| `django-hardcoded-secret-detection` | SECRET_KEY/passwords in code |
| `django-no-raw-sql` | .raw() and cursor.execute() |
| `no-debug-in-settings` | DEBUG = True in settings |
| `no-sync-in-async` | Blocking calls in async functions |
| `fastapi-missing-response-model` | FastAPI routes without response_model |

### Docker / Env / Config
| Hook ID | Purpose |
|---|---|
| `format-dockerfiles` | Format Dockerfiles (shebang, RUN merge, sort ARG/ENV) |
| `dockerfile-no-latest-detection` | FROM image:latest |
| `env-file-check` | Secrets in .env files |
| `env-example-sync` | .env.example out of sync with .env |
| `yaml-sorter` | Sort YAML keys alphabetically |
| `json-sorter` | Sort JSON keys alphabetically |
| `requirements-sort` | Sort requirements.txt/setup.cfg deps alphabetically |
| `js-syntax-check` | Node.js (.gs/.js) syntax validation |

## CI/CD

- **GitHub Actions**: `.github/workflows/ci.yml` — jobs: `version`, `lint`, `test`, `sonar`
- **Matrix**: Python 3.12, 3.13, 3.14
- **SonarCloud**: `sonar-project.properties` at root
- **Requires secrets**: `SONAR_TOKEN`, `CODECOV_TOKEN` (optional)

