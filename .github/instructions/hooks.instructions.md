---
applyTo: "pre_commit_hooks/**/*.py"
---

# Hook Architecture & Patterns

## Adding a New Hook — Checklist

1. **Create** `pre_commit_hooks/my_hook.py`
2. **Add entry point** in `setup.cfg` under `[options.entry_points] console_scripts`
3. **Register** in `.pre-commit-hooks.yaml`
4. **Write tests** in `tests/test_my_hook.py`
5. **Update README** (`tools/update_readme.py` auto-populates the hook table)

## `main()` Signature (MANDATORY)

Every hook must accept `argv`:

```python
from __future__ import annotations

import argparse
from collections.abc import Sequence

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='...')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    retval = 0
    for filename in args.filenames:
        ...
    return retval
```

## Pattern-Detection Hooks

For hooks that detect disallowed patterns in source files, inherit from `PatternDetection`:

```python
from pre_commit_hooks.tools.pattern_detection import PatternDetection

class MyDetector(PatternDetection):
    ...
```

See `console_log_detection.py` for an example.

## Disable Comments

Each hook that supports per-line suppression follows this convention:

| Hook | Disable comment |
|------|----------------|
| `python-unreachable-code` | `# unreachable-code: disable` (end of line) |
| `css-duplicate-property` | `/* css-duplicate-property: disable */` (on duplicate line) |
| `css-duplicate-id` | `/* css-duplicate-id: disable */` (on duplicate selector line) |
| `ts-unreachable-code` | `// unreachable-code: disable` (end of line) |

## Entry Points Format (`setup.cfg`)

```ini
[options.entry_points]
console_scripts =
    hook-name-detection = pre_commit_hooks.hook_module:main
    # for hooks with optional dependencies:
    ts-unreachable-code-detection = pre_commit_hooks.ts_unreachable_code_detection:main [ts_unreachable_code]
```

## `.pre-commit-hooks.yaml` Required Fields

```yaml
- id: my-hook
  name: My hook description
  language: python
  language_version: '3.12'
  entry: my-hook-detection
  types: [python]   # or types_or: [javascript, ts]
  files: \.py$
```

## Tree-Sitter Hooks (TypeScript/JS)

- Import `tree_sitter_typescript` via optional extras `[ts_unreachable_code]`
- Use `.tsx` language for `.tsx`/`.jsx` files; `.ts` language for `.ts`/`.js` files
- Walk the AST with `_walk()` returning `list[tuple[str, int, str]]` (filename, lineno, message)
