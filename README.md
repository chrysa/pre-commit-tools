# pre-commit-tools

[![CI](https://github.com/chrysa/pre-commit-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/chrysa/pre-commit-tools/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/chrysa/pre-commit-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/chrysa/pre-commit-tools)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Coverage (Sonar)](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=coverage)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/chrysa/pre-commit-tools)
[![Publish](https://github.com/chrysa/pre-commit-tools/actions/workflows/publish.yml/badge.svg)](https://github.com/chrysa/pre-commit-tools/actions/workflows/publish.yml)

A collection of **49 ready-to-use [pre-commit](https://pre-commit.com) hooks** that catch debug leftovers, leaked secrets, dead code, and framework anti-patterns before they ever reach a commit — across Python, TypeScript/React, CSS, Dockerfiles, Helm, and config files.

**Who it's for:** teams and solo developers who want a single, opinionated pre-commit repo covering Python (Django, FastAPI), TypeScript/React, and infrastructure, without wiring up a dozen separate tools.

## Why use it

- **Stop debug noise** — flag `print()`, `pprint()`, `console.log/debug/table/warn/error()`, debugger statements and root-logger calls before they land.
- **Catch leaked secrets** — hardcoded keys in `.env`, Django settings, and TypeScript/JavaScript files.
- **Find dead & unreachable code** — Python (AST + vulture) and TypeScript/JSX (tree-sitter).
- **Enforce framework best practices** — Django (no raw SQL, no `DEBUG=True`, no print in migrations), FastAPI (`response_model`, HATEOAS links), React (no direct DOM, no inline styles, no async `useEffect`).
- **Harden Dockerfiles** — no `:latest`, multi-stage builds, `HEALTHCHECK`, non-root user, auto-formatting.
- **Keep files tidy** — sort YAML / JSON / requirements keys, sync `.env` ↔ `.env.example`, lint Helm charts.

All detection hooks support an inline `disable` comment (see each hook below) to suppress a specific line.

## Installation

You don't install this package directly — [pre-commit](https://pre-commit.com) fetches it for you. Make sure pre-commit itself is installed:

```bash
pip install pre-commit   # or: pipx install pre-commit
```

## Usage

Add the repo to your project's `.pre-commit-config.yaml`, then enable only the hooks you want:

```yaml
repos:
  - repo: https://github.com/chrysa/pre-commit-tools
    rev: v0.1.1-93   # pin to a released tag
    hooks:
      # debug leftovers
      - id: python-print-detection
      - id: console-log-detection
      - id: debugger-detection
      # secrets
      - id: env-file-check
      - id: django-hardcoded-secret
      - id: ts-hardcoded-secret-detection
      # file hygiene
      - id: yaml-sorter
      - id: json-sorter
      - id: requirements-sort
      # dead / unreachable code
      - id: python-unreachable-code
      # optional — heavier, run on the manual stage to avoid false positives
      - id: python-dead-code
        stages: [manual]
```

Then install the git hook and run it:

```bash
pre-commit install
pre-commit run --all-files
```

Hooks tagged `stages: [manual]` (`python-dead-code`, `generate-changelog`) or `stages: [pre-push]` (`regression-gate`, `docs-drift-gate`) only run when explicitly invoked:

```bash
pre-commit run python-dead-code --hook-stage manual --all-files
```

## Hooks

### Debug-leftover detection

| Hook id | Detects | Inline disable |
|---|---|---|
| `python-print-detection` | `print()` in Python (excludes `tests/`) | `# print-detection: disable` |
| `python-pprint-detection` | `pprint()` in Python (excludes `tests/`) | `# pprint-detection: disable` |
| `console-debug-detection` | `console.debug()` in `.js`/`.gs`/`.ts`/`.tsx` | `// console-debug-detection: disable` |
| `console-log-detection` | `console.log()` | `// console-log-detection: disable` |
| `console-table-detection` | `console.table()` | `// console-table-detection: disable` |
| `react-console-error-detection` | `console.error()` in `.js`/`.ts`/`.jsx`/`.tsx` | `// console-error-detection: disable` |
| `no-console-warn` | `console.warn()` in `.js`/`.gs`/`.ts`/`.jsx`/`.tsx` | `// no-console-warn: disable` |
| `debugger-detection` | `breakpoint()`, `pdb`/`ipdb`/`pudb.set_trace()` | `# debugger-detection: disable` |
| `python-logger-detection` | root `logging.*` calls instead of a named logger | `# logger-detection: disable` |

### Secret detection

| Hook id | Detects |
|---|---|
| `env-file-check` | potential secrets in `.env` files (placeholders like `${VAR}`, `changeme` are ignored) |
| `django-hardcoded-secret` | `SECRET_KEY`/`PASSWORD`/`API_KEY`/`TOKEN`/`PRIVATE_KEY = "..."` in Python (env-var lookups ignored). Disable: `# django-hardcoded-secret: disable` |
| `ts-hardcoded-secret-detection` | hardcoded keys/tokens in `.js`/`.ts`/`.jsx`/`.tsx` — AWS `AKIA…`, GitHub `ghp_…`, Stripe `sk_live_…` (`process.env`/`import.meta.env` ignored). Disable: `// ts-hardcoded-secret: disable` |

### Dead & unreachable code

| Hook id | Detects | Notes |
|---|---|---|
| `python-unreachable-code` | statements after `return`/`raise`/`break`/`continue` (Python `ast`) | Disable: `# unreachable-code: disable` |
| `ts-unreachable-code` | unreachable code in `.ts`/`.tsx`/`.js`/`.jsx` (tree-sitter) | needs `tree-sitter`, `tree-sitter-typescript`. Disable: `// unreachable-code: disable` |
| `python-dead-code` | unused functions/vars/imports/classes via [vulture](https://github.com/jendrikseipp/vulture) | `manual` stage; `--min-confidence`, `--exclude`, `--whitelist` |

### Python quality

| Hook id | Detects | Inline disable |
|---|---|---|
| `no-bare-except` | bare `except:` clauses | `# no-bare-except: disable` |
| `python-no-type-ignore` | `# type: ignore` without a justification comment | — |

### Django

| Hook id | Detects | Inline disable |
|---|---|---|
| `no-print-in-migration` | `print()` in `migrations/*.py` | `# no-print-in-migration: disable` |
| `no-debug-in-settings` | `DEBUG = True` in `settings*.py` | `# no-debug-in-settings: disable` |
| `django-no-raw-sql` | `.raw()` / `cursor.execute()` (SQL-injection risk) | `# django-no-raw-sql: disable` |

### FastAPI

| Hook id | Detects | Inline disable |
|---|---|---|
| `fastapi-missing-response-model` | routes without `response_model=` | `# fastapi-missing-response-model: disable` |
| `fastapi-missing-links` | response models without a `links` field (HATEOAS) | — |
| `no-sync-in-async` | `time.sleep`/`requests.*`/`subprocess.*` inside `async def` | `# no-sync-in-async: disable` |

### React / TypeScript

| Hook id | Detects | Inline disable |
|---|---|---|
| `react-direct-dom` | `document.getElementById/querySelector` etc. in `.jsx`/`.tsx` | `// react-direct-dom: disable` |
| `react-no-inline-styles` | `style={{…}}` inline styles in `.jsx`/`.tsx` | — |
| `react-no-async-in-useeffect` | async function passed directly to `useEffect()` | — |
| `import-no-relative-parent` | deep relative parent imports (`../../`) — prefer `@/` aliases | `// import-no-relative-parent: disable` |
| `ts-no-any` | explicit `any` (`: any`, `as any`, `<any>`) in `.ts`/`.tsx` (excludes tests) | — |
| `js-syntax-check` | invalid `.js`/`.gs` syntax via `node --check` (skips if Node absent) | — |

### CSS

| Hook id | Detects | Inline disable |
|---|---|---|
| `css-duplicate-property` | duplicate property declarations and duplicate `#id` selectors | `/* css-duplicate-property: disable */`, `/* css-duplicate-id: disable */` |
| `css-unused-variable` | `--custom-properties` declared but never used via `var()` | `/* css-unused-variable: disable */` |

### Dockerfiles

| Hook id | What it does |
|---|---|
| `format-dockerfiles` | format & normalize Dockerfiles (see options below) |
| `dockerfile-no-latest` | reject `FROM image:latest` (`scratch` allowed). Disable: `# dockerfile-no-latest: disable` |
| `dockerfile-multi-stage-check` | require a multi-stage build (≥ 2 `FROM` stages) |
| `dockerfile-healthcheck` | require a `HEALTHCHECK` in the final stage |
| `dockerfile-non-root-user` | reject final stage running as root (no `USER` / `USER root`) |

### Infra, config & files

| Hook id | What it does |
|---|---|
| `yaml-sorter` | sort YAML keys alphabetically (in-place) |
| `json-sorter` | sort JSON keys alphabetically (in-place) |
| `requirements-sort` | sort `requirements*.txt` and `setup.cfg` dependencies |
| `env-example-sync` | check `.env` and `.env.example` have the same keys |
| `no-hardcoded-localhost` | reject hardcoded `localhost`/`127.0.0.1` URLs in `.py`/`.ts`/`.tsx`/`.js`/`.jsx` (excludes tests) |
| `helm-lint` | `helm lint --strict` on `charts/<namespace>/<service>/` (skips if `helm` absent) |
| `makefile-check` | enforce the chrysa tiered Makefile contract |
| `pylint-with-html-report` | run Pylint and emit an HTML report |

### Project governance (chrysa-specific)

| Hook id | What it does | Stage |
|---|---|---|
| `adr-gate` | require a `DECISIONS.md` update when architecture-sensitive files change | commit |
| `detect-duplicated-copilot-instructions` | flag per-repo `copilot-instructions.md` sections already in workspace-level instructions | commit |
| `generate-changelog` | (re)generate `CHANGELOG.md` from git history via [git-cliff](https://github.com/orhun/git-cliff) | `manual` |
| `regression-gate` | block push if coverage or test count regresses below `.quality-baseline.json` | `pre-push` |
| `docs-drift-gate` | regenerate code-derived docs and block push if they drift from the committed copy | `pre-push` |

## Hook options

### `format-dockerfiles`

- Adds `# syntax=docker/dockerfile:1.4` shebang if missing.
- Groups consecutive same-instruction blocks; merges consecutive `RUN`/`ENV` into one command.

| Option | Description |
|---|---|
| `--sort-args` | sort `ARG` instructions alphabetically |
| `--sort-envs` | sort `ENV` instructions alphabetically |
| `--separate-arg-blocks` | separate literal `ARG` from variable-dependent `ARG` (e.g. `ARG FOO=${BAR}`) |
| `-c / --config` | path to a `.format-dockerfiles.toml` config file |

```toml
# .format-dockerfiles.toml
[format-dockerfiles]
sort_args = true
sort_envs = true
separate_arg_blocks = true
```

### `python-dead-code`

| Option | Default | Description |
|---|---|---|
| `--min-confidence` | `80` | minimum confidence % to report (0–100) |
| `--exclude` | — | space-separated glob patterns to skip |
| `--whitelist` | — | vulture whitelist `.py` files to suppress false positives |

```yaml
- id: python-dead-code
  stages: [manual]
  args:
    - '--min-confidence=80'
    - '--exclude=tests/ migrations/ **/conftest.py'
    - '--whitelist=whitelist.py'
  additional_dependencies: [vulture>=2.0]
```

> vulture may produce false positives on names used only via `getattr`, `__all__`, decorators, or dynamic dispatch — use a [whitelist file](https://github.com/jendrikseipp/vulture#whitelists). This hook runs in the `manual` stage by default to avoid false positives on entry points.

### `pylint-with-html-report`

| Option | Default | Description |
|---|---|---|
| `--output-html` | `./html` | directory where the HTML report is written |
| `--output-json` | auto-deleted | path for the intermediate JSON report; deleted after conversion unless specified |

```yaml
- id: pylint-with-html-report
  additional_dependencies: [pylint, pylint-report]
  args:
    - '--output-html=reports/pylint'
    - '--output-json=pylint.json'
```

### `env-example-sync`

| Option | Default | Description |
|---|---|---|
| `--env-file` | `.env` | path to the private `.env` file |
| `--example-file` | `.env.example` | path to the public example file |

### `makefile-check`

Enforces the chrysa archetype-tiered Makefile contract (shared-standards `EXECUTION_STANDARD.md` §1). Each Makefile must declare its tier:

```makefile
# makefile-tier: lib        # one of: lib | python-app | fullstack | infra
```

Fails on a missing/invalid tier marker, a required target absent for the tier, a forbidden target name (`fmt`/`type-check`/`tests`), a legacy `docker-compose <cmd>` invocation, a glued `docker compose` typo, a missing `help` target or `.PHONY` line, or a lint/test/format rule referencing a directory that does not exist. Missing `.PHONY` entries and absent `## ` self-documenting comments are reported as warnings.

## Related

- [chrysa/guideline-checker](https://github.com/chrysa/guideline-checker) — structural coding-guidelines checker (project structure, naming, standards), usable as a companion pre-commit hook.

## License

MIT
