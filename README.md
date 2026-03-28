# pre-commit-tools

<!--TOC-->

- [pre-commit-tools](#pre-commit-tools)
  - [Using pre-commit-tools with pre-commit](#using-pre-commit-tools-with-pre-commit)
  - [Hooks available](#hooks-available)
    - [format-dockerfiles](#format-dockerfiles)
      - [Description](#description)
      - [Todo](#todo)
    - [python-print-detection](#python-print-detection)
    - [python-pprint-detection](#python-pprint-detection)
    - [console-debug-detection](#console-debug-detection)
    - [console-log-detection](#console-log-detection)
    - [console-table-detection](#console-table-detection)
    - [\[WIP\] pylint-html-report](#wip-pylint-html-report)
    - [yaml-sorter](#yaml-sorter)
    - [debugger-detection](#debugger-detection)
    - [json-sorter](#json-sorter)
    - [requirements-sort](#requirements-sort)
    - [env-file-check](#env-file-check)
    - [python-logger-detection](#python-logger-detection)
    - [python-unreachable-code](#python-unreachable-code)
    - [python-dead-code](#python-dead-code)

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
          - id: format-dockerfiles
          - id: python-print-detection
          - id: python-pprint-detection
          - id: yaml-sorter
          - id: debugger-detection
          - id: json-sorter
          - id: requirements-sort
          - id: env-file-check
          - id: python-logger-detection
          - id: python-unreachable-code
          # optional — run manually: pre-commit run python-dead-code --hook-stage manual --all-files
          - id: python-dead-code
            stages: [manual]
            additional_dependencies: [vulture>=2.0]
```

## Hooks available

### format-dockerfiles

#### Description

- add shebang `# syntax=docker/dockerfile:1.4` if missing
- group consecutive same command without space
- group consecutive `RUN` or `ENV` on one command line with new line

#### Todo

- separate block for literal ARGS and ARGS composed with variable
- order alphabetically ARGS
- order alphabetically ENV
- add config file support

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

### [WIP] pylint-html-report

Generate pylint HTML reports.
Use `--output-json` to define JSON output and `--output-html` to specify HTML output.

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

Sort `requirements*.txt` files alphabetically (comments and blank lines first, then packages sorted case-insensitively). Modifies files in-place and returns 1 if any file was changed.

### env-file-check

Detect potential secrets committed in `.env` files (passwords, tokens, API keys, etc.).
Placeholder values (`<value>`, `${VAR}`, `changeme`, etc.) are ignored.

### python-logger-detection

Detect direct use of the root `logging` module (e.g. `logging.info(...)`) instead of a named logger.
Use `# logger-detection: disable` to ignore a specific line.

### python-unreachable-code

Detect **explicit** unreachable code — statements after `return`, `raise`, `break`, or `continue` — using Python's `ast` module. Works with Python 3.12, 3.13 and 3.14.

No configuration needed. Returns 1 if any unreachable statement is found.

```python
def f():
    return 1
    x = 2  # ← detected: unreachable code after return
```

### python-dead-code

Detect **implicit** dead/unused code (unused functions, variables, imports, classes) using [vulture](https://github.com/jendrikseipp/vulture).

This hook runs in the `manual` stage by default to avoid false positives on entry points.

```yaml
- id: python-dead-code
  stages: [manual]
  args: ['--min-confidence=80']
  additional_dependencies: [vulture>=2.0]
```

Run manually:

```bash
pre-commit run python-dead-code --hook-stage manual --all-files
```

