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

<!--TOC-->

Some out-of-the-box hooks for pre-commit.

## Using pre-commit-tools with pre-commit

Add this to your `.pre-commit-config.yaml`

```yaml
-   repo: https://github.com/chrysa/pre-commit-tools
    rev: ''  # Use the ref you want to point at
    hooks:
    -   id: format-dockerfiles
        stages:
            - manual
    -   id: print-detection
    -   id: pprint-detection
```

## Hooks available

### format-dockerfiles

#### Description

- add shebang `# syntax=docker/dockerfile:1.4` if missing
- group donsecutif same command without space
- group consecutive `RUN` or `ENV` on one commande line with new line

#### Todo

- separate block for litteral ARGS and ARGS composed with variable
- order alphabeticly ARGS
- order alphabeticly ENV
- add config file support

### python-print-detection

detect print on python code if is not commented or excape with `# print-detection: disable`

### python-pprint-detection

detect pprint on python code if is not commented or excape with `# pprint-detection: disable`

### [WIP] pylint-html-report

generate pylint html reports
use `--=output-json` to define json output and `--output-html=` to specify html output
