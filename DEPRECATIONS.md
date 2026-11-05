# Deprecated hooks

The hooks below re-implement, with line-based regexes or a home-grown AST walk, a rule
that a mainstream linter already ships natively. The native rule is AST/parser based
(no false positives inside strings or docstrings, no misses on `x && console.log()`),
supports standard inline suppressions (`# noqa`, `eslint-disable-next-line`) and is
already in most consumers' toolchain.

**Status:** deprecated, still functional. Each hook keeps its exit code and output, and
prints a migration notice on stderr. They will be removed in a future minor release.

## Summary

| Hook id | Native replacement | Coverage gap |
|---|---|---|
| `python-print-detection` | ruff `T201` | none |
| `python-pprint-detection` | ruff `T203` | none |
| `debugger-detection` | ruff `T100` (or `debug-statements` from pre-commit-hooks) | none |
| `no-print-in-migration` | ruff `T201` | none (scope with `per-file-ignores`) |
| `no-bare-except` | ruff `E722` | none |
| `python-mutable-default` | ruff `B006` | none |
| `python-logger-detection` | ruff `LOG015` | none |
| `no-sync-in-async` | ruff `ASYNC210`, `ASYNC212`, `ASYNC220`-`ASYNC222`, `ASYNC230`, `ASYNC251` | `input()` |
| `console-log-detection` | ESLint `no-console` | none |
| `console-debug-detection` | ESLint `no-console` | none |
| `console-table-detection` | ESLint `no-console` | none |
| `no-console-warn` | ESLint `no-console` | none |
| `react-console-error-detection` | ESLint `no-console` | none |
| `ts-no-any` | typescript-eslint `@typescript-eslint/no-explicit-any` | none |
| `ts-unreachable-code` | ESLint `no-unreachable` + tsc `allowUnreachableCode: false` | none |
| `dockerfile-no-latest` | hadolint `DL3007` (+ `DL3006` for untagged images) | none |

## Python hooks -> ruff

### 1. Remove the deprecated hooks from `.pre-commit-config.yaml`

```yaml
  - repo: https://github.com/chrysa/pre-commit-tools
    rev: <your rev>
    hooks:
      # remove these ids:
      # - id: python-print-detection
      # - id: python-pprint-detection
      # - id: debugger-detection
      # - id: no-print-in-migration
      # - id: no-bare-except
      # - id: python-mutable-default
      # - id: python-logger-detection
      # - id: no-sync-in-async
```

### 2. Make sure ruff runs in pre-commit

```yaml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.7
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

### 3. Enable the rules in `pyproject.toml`

```toml
[tool.ruff.lint]
extend-select = [
    "T10",   # flake8-debugger      -> replaces debugger-detection
    "T20",   # flake8-print         -> replaces python-print-detection, python-pprint-detection, no-print-in-migration
    "E722",  # bare except          -> replaces no-bare-except (already in "E")
    "B006",  # mutable default      -> replaces python-mutable-default (already in "B")
    "LOG",   # flake8-logging       -> replaces python-logger-detection (LOG015)
    "ASYNC", # flake8-async         -> replaces no-sync-in-async
]

[tool.ruff.lint.per-file-ignores]
# Keep the old `exclude: tests?/` behaviour of the print hooks.
"tests/**" = ["T20"]
# CLI entry points that print on purpose.
"scripts/**" = ["T201"]
```

### 4. Convert inline opt-outs

| Old comment | New comment |
|---|---|
| `# print-detection: disable` | `# noqa: T201` |
| `# pprint-detection: disable` | `# noqa: T203` |
| `# debugger-detection: disable` | `# noqa: T100` |
| `# no-print-in-migration: disable` | `# noqa: T201` |
| `# no-bare-except: disable` | `# noqa: E722` |
| `# python-mutable-default: disable` | `# noqa: B006` |
| `# logger-detection: disable` | `# noqa: LOG015` |
| `# no-sync-in-async: disable` | `# noqa: ASYNC<code>` (code printed by ruff) |

One-shot conversion:

```bash
git grep -lE '(print|pprint|debugger|logger)-detection: disable|no-(bare-except|print-in-migration|sync-in-async): disable|python-mutable-default: disable' -- '*.py' \
  | xargs sed -i -E \
    -e 's/# ?print-detection: disable/# noqa: T201/' \
    -e 's/# ?pprint-detection: disable/# noqa: T203/' \
    -e 's/# ?debugger-detection: disable/# noqa: T100/' \
    -e 's/# ?no-print-in-migration: disable/# noqa: T201/' \
    -e 's/# ?no-bare-except: disable/# noqa: E722/' \
    -e 's/# ?python-mutable-default: disable/# noqa: B006/' \
    -e 's/# ?logger-detection: disable/# noqa: LOG015/'
ruff check .   # then fix the remaining no-sync-in-async opt-outs by hand with the code ruff reports
```

### Behaviour differences

- `no-sync-in-async`: ruff does not flag `input()` inside `async def`. Keep a code review
  check, or ban it with `flake8-tidy-imports` (`TID251`) if it matters to you.
- `python-mutable-default`: B006 also flags `collections.OrderedDict()` and similar; extra
  immutable factories can be whitelisted with
  `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls = [...]`.
- All ruff rules are AST based: a `print(` inside a string or docstring is no longer
  reported, and multi-line calls are reported on the right line.

## JavaScript / TypeScript hooks -> ESLint

### 1. Remove from `.pre-commit-config.yaml`

`console-log-detection`, `console-debug-detection`, `console-table-detection`,
`no-console-warn`, `react-console-error-detection`, `ts-no-any`, `ts-unreachable-code`.

### 2. Enable the rules (flat config, `eslint.config.js`)

```js
import tseslint from 'typescript-eslint';

export default tseslint.config(
  ...tseslint.configs.recommended, // ships no-explicit-any
  {
    rules: {
      // replaces console-log/debug/table-detection, no-console-warn, react-console-error-detection
      'no-console': 'error',
      // or keep one level allowed, e.g. the old react-console-error-detection opt-out:
      // 'no-console': ['error', { allow: ['error'] }],
      '@typescript-eslint/no-explicit-any': 'error', // replaces ts-no-any
      'no-unreachable': 'error',                      // replaces ts-unreachable-code
    },
  },
);
```

And in `tsconfig.json`:

```json
{ "compilerOptions": { "allowUnreachableCode": false } }
```

### 3. Run ESLint from pre-commit (pnpm, local hook)

```yaml
  - repo: local
    hooks:
      - id: eslint
        name: eslint
        entry: pnpm exec eslint --max-warnings=0
        language: system
        types_or: [javascript, jsx, ts, tsx]
```

### 4. Convert inline opt-outs

| Old comment | New comment |
|---|---|
| `// console-log-detection: disable` (and the debug/table/warn/error variants) | `// eslint-disable-next-line no-console` |
| `// ts-no-any: disable` | `// eslint-disable-next-line @typescript-eslint/no-explicit-any` |

### Behaviour differences

- `.gs` (Google Apps Script) files: add `files: ['**/*.gs']` to an ESLint config block,
  otherwise ESLint ignores them.
- ESLint flags every `console.*` call, not only calls at the start of a line
  (`cond && console.log(x)` was silently missed by the old hooks).

## Dockerfile hook -> hadolint

```yaml
  - repo: https://github.com/hadolint/hadolint
    rev: v2.15.1
    hooks:
      - id: hadolint-docker   # runs in a container, no local binary needed
        # Same scope as the old hook: only untagged / :latest images block the commit.
        # Drop these args to adopt the full hadolint rule set.
        args: [--error, DL3006, --error, DL3007, --failure-threshold, error]
        files: (^|/)Dockerfile[^/]*$
        types: [file]
```

| Old comment | New comment (line above the `FROM`) |
|---|---|
| `# dockerfile-no-latest: disable` | `# hadolint ignore=DL3007` |

hadolint also reports `FROM image` without any tag (`DL3006`), which the old hook missed.
