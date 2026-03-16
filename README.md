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
    - [\[WIP\] pylint-html-report](#wip-pylint-html-report)
    - [requirements-sort](#requirements-sort)
    - [env-file-check](#env-file-check)
    - [logger-detection](#logger-detection)

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
            stages:
              - manual
          - id: print-detection
          - id: pprint-detection
          - id: yaml-sorter
          - id: requirements-sort
          - id: env-file-check
          - id: logger-detection
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

detect print on python code if is not commented or escaped with `# print-detection: disable`

### python-pprint-detection

detect pprint on python code if is not commented or escaped with `# pprint-detection: disable`

### [WIP] pylint-html-report

generate pylint html reports
use `--output-json` to define json output and `--output-html` to specify html output

### requirements-sort

Sort `requirements*.txt` files alphabetically (comments and blank lines first, then packages sorted case-insensitively). Modifies files in-place and returns 1 if any file was changed.
### env-file-check

Detect potential secrets committed in `.env` files (passwords, tokens, API keys, etc.).
Placeholder values (`<value>`, `${VAR}`, `changeme`, etc.) are ignored.
### logger-detection

Detect direct use of the root `logging` module (e.g. `logging.info(...)`) instead of a named logger.
Use `# logger-detection: disable` to ignore a specific line.
