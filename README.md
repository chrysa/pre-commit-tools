# pre-commit-tools

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
    - [pylint-html-report](#pylint-html-report)
    - [yaml-sorter](#yaml-sorter)
    - [debugger-detection](#debugger-detection)
    - [json-sorter](#json-sorter)
    - [requirements-sort](#requirements-sort)
    - [env-file-check](#env-file-check)
    - [python-logger-detection](#python-logger-detection)
    - [python-unreachable-code](#python-unreachable-code)
    - [python-dead-code](#python-dead-code)
    - [ts-unreachable-code](#ts-unreachable-code)
    - [css-duplicate-property](#css-duplicate-property)

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
          - id: ts-unreachable-code
          - id: css-duplicate-property
```

## Hooks available

### format-dockerfiles

- Add shebang `# syntax=docker/dockerfile:1.4` if missing
- Group consecutive same-instruction blocks without blank lines
- Merge consecutive `RUN` or `ENV` instructions on one command line with continuation

Open enhancements tracked as GitHub issues:
- [#43](https://github.com/chrysa/pre-commit-tools/issues/43) Separate literal `ARG` blocks from variable-dependent `ARG`s
- [#44](https://github.com/chrysa/pre-commit-tools/issues/44) Sort `ARG` instructions alphabetically
- [#47](https://github.com/chrysa/pre-commit-tools/issues/47) Sort `ENV` instructions alphabetically
- [#48](https://github.com/chrysa/pre-commit-tools/issues/48) Add config file support

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

