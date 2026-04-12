# pre-commit-tools

[![CI](https://github.com/chrysa/pre-commit-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/chrysa/pre-commit-tools/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/chrysa/pre-commit-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/chrysa/pre-commit-tools)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Coverage (Sonar)](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=coverage)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=chrysa_pre-commit-tools&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=chrysa_pre-commit-tools)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pre-commit-hooks-tools)](https://pypi.org/project/pre-commit-hooks-tools/)
[![Publish](https://github.com/chrysa/pre-commit-tools/actions/workflows/publish.yml/badge.svg)](https://github.com/chrysa/pre-commit-tools/actions/workflows/publish.yml)

<!--TOC-->

- [pre-commit-tools](#pre-commit-tools)
  - [Using pre-commit-tools with pre-commit](#using-pre-commit-tools-with-pre-commit)
  - [Hooks available](#hooks-available)
    - [format-dockerfiles](#format-dockerfiles)
    - [python-print-detection](#python-print-detection)
    - [python-pprint-detection](#python-pprint-detection)
    - [console-debug-detection](#console-debug-detection)
    - [console-log-detection](#console-log-detection)
    - [console-table-detection](#console-table-detection)
    - [react-console-error-detection](#react-console-error-detection)
    - [pylint-html-report](#pylint-html-report)
    - [yaml-sorter](#yaml-sorter)
    - [debugger-detection](#debugger-detection)
    - [json-sorter](#json-sorter)
    - [requirements-sort](#requirements-sort)
    - [env-file-check](#env-file-check)
    - [env-example-sync](#env-example-sync)
    - [python-logger-detection](#python-logger-detection)
    - [python-unreachable-code](#python-unreachable-code)
    - [python-dead-code](#python-dead-code)
    - [no-bare-except](#no-bare-except)
    - [no-print-in-migration](#no-print-in-migration)
    - [django-hardcoded-secret](#django-hardcoded-secret)
    - [dockerfile-no-latest](#dockerfile-no-latest)
    - [ts-unreachable-code](#ts-unreachable-code)
    - [css-duplicate-property](#css-duplicate-property)
    - [css-unused-variable](#css-unused-variable)

<!--TOC-->

Some out-of-the-box hooks for pre-commit.

## Using pre-commit-tools with pre-commit

Add this to your `.pre-commit-config.yaml`

```yaml
-   repo: https://github.com/chrysa/pre-commit-tools
    rev: ''  # Use the ref you want to point at
    hooks:
          - id: console-debug-detection
          - id: console-log-detection
          - id: console-table-detection
          - id: react-console-error-detection
          - id: format-dockerfiles
          - id: dockerfile-no-latest
          - id: python-print-detection
          - id: python-pprint-detection
          - id: no-bare-except
          - id: no-print-in-migration
          - id: django-hardcoded-secret
          - id: yaml-sorter
          - id: debugger-detection
          - id: json-sorter
          - id: requirements-sort
          - id: env-file-check
          - id: env-example-sync
          - id: python-logger-detection
          - id: python-unreachable-code
          # optional — run manually: pre-commit run python-dead-code --hook-stage manual --all-files
          - id: python-dead-code
            stages: [manual]
          - id: ts-unreachable-code
          - id: css-duplicate-property
          - id: css-unused-variable
          # requires helm in PATH
          - id: helm-lint

# Optional — guideline-checker (structural coding guidelines)
# Validates project structure, naming conventions, and coding standards.
# See https://github.com/chrysa/guideline-checker
#-  repo: https://github.com/chrysa/guideline-checker
#   rev: ''  # Use the ref you want to point at
#   hooks:
#     - id: guideline-check
#       stages: [pre-push, manual]
```

## Hooks available

### format-dockerfiles

- Add shebang `# syntax=docker/dockerfile:1.4` if missing
- Group consecutive same-instruction blocks without blank lines
- Merge consecutive `RUN` or `ENV` instructions on one command line with continuation

**New options:**

| Option | Description |
|---|---|
| `--sort-args` | Sort `ARG` instructions alphabetically |
| `--sort-envs` | Sort `ENV` instructions alphabetically |
| `--separate-arg-blocks` | Separate literal `ARG` from variable-dependent `ARG` (e.g. `ARG FOO=${BAR}`) |
| `-c / --config` | Path to a `.format-dockerfiles.toml` config file |

Config file example (`.format-dockerfiles.toml`):

```toml
[format-dockerfiles]
sort_args = true
sort_envs = true
separate_arg_blocks = true
```

### python-print-detection

Detect `print()` calls in Python files. Use `# print-detection: disable` to ignore a specific line.

### python-pprint-detection

Detect `pprint()` calls in Python files. Use `# pprint-detection: disable` to ignore a specific line.

### console-debug-detection

Detect `console.debug()` calls in JavaScript/Google AppScript (`.js`, `.gs`) files.
Use `// console-debug-detection: disable` to ignore a specific line.

### console-log-detection

Detect `console.log()` calls in JavaScript/Google AppScript files.
Use `// console-log-detection: disable` to ignore a specific line.

### console-table-detection

Detect `console.table()` calls in JavaScript/Google AppScript files.
Use `// console-table-detection: disable` to ignore a specific line.

### pylint-html-report

Run [Pylint](https://pylint.org) over Python files and generate an HTML report via [pylint-report](https://github.com/ddeepwell/pylint-report).

```yaml
- id: pylint-with-html-report
  additional_dependencies: [pylint, pylint-report]
  args:
    - '--output-html=reports/pylint'   # directory for the HTML report (default: ./html)
    - '--output-json=pylint.json'      # keep the intermediate JSON (omit to auto-delete)
```

| Option | Default | Description |
|---|---|---|
| `--output-html` | `./html` | Directory where the HTML report is written |
| `--output-json` | auto-deleted | Path for the intermediate JSON report; deleted after conversion unless specified |

### yaml-sorter

Sort YAML file keys alphabetically (recursive). Modifies files in-place and returns 1 if any file was changed.
To skip a file, exclude it in your `.pre-commit-config.yaml`.
Boolean and mixed-type keys are handled safely.

### debugger-detection

Detect debugger statements (`breakpoint()`, `pdb.set_trace()`, `ipdb.set_trace()`, `pudb.set_trace()`) in Python files.
Use `# debugger-detection: disable` to ignore a specific line.

### json-sorter

Sort JSON file keys alphabetically (recursive). Modifies files in-place and returns 1 if any file was changed.

### requirements-sort

Sort Python dependency files alphabetically. Modifies files in-place and returns 1 if any file was changed.

**Supported files**

| File pattern | What is sorted |
|---|---|
| `requirements*.txt` | All package lines (case-insensitive); comments and blank lines are moved to the top |
| `setup.cfg` | `install_requires` entries; extras keys in `[options.extras_require]` and their dependencies |

**Example — setup.cfg**

```ini
# Before
[options.extras_require]
yaml =
    PyYAML==6.0.1
dead_code =
    vulture>=2.0
    aardvark>=1.0

# After
[options.extras_require]
dead_code =
    aardvark>=1.0
    vulture>=2.0
yaml =
    PyYAML==6.0.1
```

### env-file-check

Detect potential secrets committed in `.env` files (passwords, tokens, API keys, etc.).
Placeholder values (`<value>`, `${VAR}`, `changeme`, etc.) are ignored.

### python-logger-detection

Detect direct use of the root `logging` module (e.g. `logging.info(...)`) instead of a named logger.
Use `# logger-detection: disable` to ignore a specific line.

### python-unreachable-code

Detect **explicit** unreachable code — statements after `return`, `raise`, `break`, or `continue` — using Python's `ast` module. Works with Python 3.12, 3.13 and 3.14.

**Language**: Python only (AST-based, no external dependency).

No configuration needed. Returns 1 if any unreachable statement is found.

```python
def f():
    return 1
    x = 2  # ← detected: unreachable code after return
```

Use `# unreachable-code: disable` on the unreachable line to suppress a specific violation.

### python-dead-code

Detect **implicit** dead/unused code (unused functions, variables, imports, classes) using [vulture](https://github.com/jendrikseipp/vulture).

**Language**: Python only. **Not language-agnostic** — vulture analyses Python ASTs.

**Dynamic code generation**: vulture may produce false positives on names used only via `getattr`, `__all__`, decorators, or dynamic dispatch. Use a [whitelist file](https://github.com/jendrikseipp/vulture#whitelists) to suppress them.

This hook runs in the `manual` stage by default to avoid false positives on entry points.

```yaml
- id: python-dead-code
  stages: [manual]
  args:
    - '--min-confidence=80'
    # Exclude paths matching these glob patterns
    - '--exclude=tests/ migrations/ **/conftest.py'
    # Whitelist file listing names used dynamically (suppresses false positives)
    - '--whitelist=whitelist.py'
  additional_dependencies: [vulture>=2.0]
```

| Option | Default | Description |
|---|---|---|
| `--min-confidence` | `80` | Minimum confidence % to report (0–100) |
| `--exclude` | — | Space-separated glob patterns of paths to skip |
| `--whitelist` | — | Vulture whitelist `.py` files to suppress false positives |

Run manually:

```bash
pre-commit run python-dead-code --hook-stage manual --all-files
```

### ts-unreachable-code

Detect **explicit** unreachable code — statements after `return`, `throw`, `break`, or `continue` — in TypeScript (`.ts`), TSX (`.tsx`), JavaScript (`.js`) and JSX (`.jsx`) files, using a real AST via [tree-sitter](https://github.com/tree-sitter/tree-sitter).

**Language**: TypeScript / TSX / JavaScript / JSX (React). The TSX parser is used for `.tsx`/`.jsx` to handle JSX syntax.

**Dynamic code generation**: tree-sitter performs syntactic analysis only, so dynamically evaluated code is unaffected.

Use `// unreachable-code: disable` on the unreachable line to suppress a specific violation.

```typescript
function f() {
  throw new Error('not implemented');
  return 42;  // ← detected: unreachable code after throw
}
```

```yaml
- id: ts-unreachable-code
  additional_dependencies:
    - tree-sitter>=0.23
    - tree-sitter-typescript>=0.23
```

### css-duplicate-property

Detect **duplicate CSS property declarations** within the same rule block, and **duplicate `#id` selectors** across the stylesheet. Duplicate properties hide the first declaration; duplicate IDs violate CSS specificity best-practices and make maintenance harder.

**Language**: CSS (`.css`). SCSS/Less are not currently supported.

Use `/* css-duplicate-property: disable */` on the duplicate property line to suppress a specific violation.
Use `/* css-duplicate-id: disable */` on the duplicate ID selector line to suppress a specific violation.

```css
.foo {
  color: red;    /* ← first declaration */
  color: blue;   /* ← detected: duplicate property "color" (first at line 2) */
}

#hero { color: red; }   /* ← first occurrence */
#hero { color: blue; }  /* ← detected: duplicate ID selector "hero" (first at line 6) */
```

Nested rule blocks are tracked independently (each `{…}` scope has its own seen-properties map).

### css-unused-variable

Detect **CSS custom properties** (`--var-name`) that are declared but never used anywhere in the file via `var(--var-name)`.

**Language**: CSS (`.css`). SCSS/Less are not currently supported.

Use `/* css-unused-variable: disable */` on the declaration line to suppress a specific violation.

```css
:root {
  --color-primary: #007bff;  /* ← used below */
  --color-ghost: #aaa;       /* ← detected: declared but never used */
}
.btn { color: var(--color-primary); }
```

### react-console-error-detection

Detect `console.error()` calls in JavaScript/TypeScript/React files. Complements `console-log-detection`, `console-debug-detection` and `console-table-detection`.

**Language**: `.js`, `.ts`, `.jsx`, `.tsx`.

Use `// console-error-detection: disable` on the line to suppress a specific violation.

### no-bare-except

Detect bare `except:` clauses (without specifying an exception type) in Python files. Bare excepts catch all exceptions including `SystemExit`, `KeyboardInterrupt` and `GeneratorExit`, which can mask serious errors.

Use `# no-bare-except: disable` to suppress a specific line.

```python
# WRONG
try:
    do_something()
except:          # ← detected
    pass

# OK
try:
    do_something()
except ValueError:
    pass
```

### no-print-in-migration

Detect `print()` calls in Django migration files (`migrations/*.py`). Print statements committed in migrations will be shown every time migrations run.

Use `# no-print-in-migration: disable` to suppress a specific line.

### django-hardcoded-secret

Detect hardcoded secrets directly assigned in Python files. Catches patterns like `SECRET_KEY = "..."`, `PASSWORD = "..."`, `API_KEY = "..."`, `TOKEN = "..."` and `PRIVATE_KEY = "..."`.

Values referencing environment variables (`os.environ`, `os.getenv`, `env()`, `config()`, etc.) are **not** flagged.

Use `# django-hardcoded-secret: disable` to suppress a specific line.

```python
# WRONG — detected
SECRET_KEY = 'django-insecure-abc123'

# OK — not flagged
SECRET_KEY = os.environ['SECRET_KEY']
SECRET_KEY = env('SECRET_KEY')
```

### dockerfile-no-latest

Detect `FROM image:latest` instructions in Dockerfiles. Using `:latest` makes builds non-reproducible.
`FROM scratch` is always allowed.

Use `# dockerfile-no-latest: disable` to suppress a specific line.

```dockerfile
# WRONG
FROM python:latest

# OK
FROM python:3.12-slim
```

### env-example-sync

Check that `.env` and `.env.example` files contain the same set of keys. Ensures that new environment variables added to `.env` are documented in `.env.example` (with empty or placeholder values), and vice-versa.

```yaml
- id: env-example-sync
  args:
    - '--env-file=.env'           # default
    - '--example-file=.env.example'  # default
```

| Option | Default | Description |
|---|---|---|
| `--env-file` | `.env` | Path to the private `.env` file |
| `--example-file` | `.env.example` | Path to the public example file |

---

### no-console-warn

Detect `console.warn()` calls in JavaScript/TypeScript/React files (`.js`, `.gs`, `.ts`, `.jsx`, `.tsx`).
Use `// no-console-warn: disable` to suppress a specific line.

### react-direct-dom

Detect direct DOM manipulation (`document.getElementById`, `document.querySelector`, etc.) in React files (`.jsx`, `.tsx`).
Direct DOM access bypasses React's virtual DOM — use refs or state instead.
Use `// react-direct-dom: disable` to suppress a specific line.

### import-no-relative-parent

Detect deep relative parent imports (`../../`) in TypeScript/JavaScript files.
Use path aliases (`@/`) instead. Two or more `../` levels trigger a violation.
Use `// import-no-relative-parent: disable` to suppress a specific line.

### no-debug-in-settings

Detect `DEBUG = True` in Django settings files (`settings*.py`).
Use `# no-debug-in-settings: disable` to suppress a specific line.

### django-no-raw-sql

Detect raw SQL queries (`.raw()` and `cursor.execute()`) in Django Python files.
These patterns bypass the ORM and risk SQL injection.
Use `# django-no-raw-sql: disable` to suppress a specific line.

### no-sync-in-async

Detect synchronous blocking calls inside `async def` functions:

| Blocked call | Suggested async replacement |
|---|---|
| `time.sleep()` | `asyncio.sleep()` |
| `requests.get/post/put/delete/patch()` | `httpx.AsyncClient` or `aiohttp` |
| `subprocess.run/call/check_output()` | `asyncio.create_subprocess_exec` |

Use `# no-sync-in-async: disable` to suppress a specific line.

### fastapi-missing-response-model

Detect FastAPI route handlers (`@app.get`, `@app.post`, etc.) that do not declare a `response_model=` parameter.
This prevents automatic response schema generation and validation.
Use `# fastapi-missing-response-model: disable` on the decorator line to suppress.

```yaml
- id: fastapi-missing-response-model
  files: '(routers?|views?|api)/.*\.py$'
```

### js-syntax-check

Validate JavaScript and Google Apps Script (`.js`, `.gs`) file syntax using `node --check`.
Requires Node.js to be installed in PATH. If Node.js is not available, the hook exits 0 (safe skip).

```yaml
- id: js-syntax-check
  files: '\.(js|gs)$'
```

### helm-lint

Run `helm lint --strict` on all charts found in `charts/<namespace>/<service>/` (depth 2 under `charts/`).
Requires `helm` to be installed in PATH.

Expected directory structure:

```text
charts/
  <namespace>/
    <service>/     ← helm lint --strict is run here
      Chart.yaml
      values.yaml
```

```yaml
- id: helm-lint
  files: ^charts/
  pass_filenames: false
```
