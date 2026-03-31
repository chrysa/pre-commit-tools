---
applyTo: "pre_commit_hooks/**/*.py"
---

# Python Development Guidelines

## Tech Stack

- **Python**: 3.12+ (target 3.14, retrocompatible 3.12)
- **Linting/Formatting**: Ruff (`config-tools/ruff.toml`) — replaces flake8, Black, isort
- **Type Checking**: mypy (`setup.cfg [mypy]`)
- **Testing**: pytest + pytest-cov

## Golden Rule

Ruff is the source of truth. If it fails, fix it. No exceptions.

```bash
ruff check --config=config-tools/ruff.toml pre_commit_hooks tests
ruff format --check --config=config-tools/ruff.toml pre_commit_hooks
mypy --config-file=setup.cfg pre_commit_hooks
```

---

## Python Version Targets

```python
# Use modern syntax — works on 3.12+
x: list[str]           # PEP 585 — not List[str]
x: str | None          # PEP 604 — not Optional[str]
x: dict[str, int]      # PEP 585 — not Dict[str, int]
```

No `from __future__ import annotations` needed for 3.12+, but keep it for
compatibility signals — all existing hooks use it.

---

## Type Annotations (MANDATORY)

All public functions and methods must have complete type annotations:

```python
# CORRECT
def detect_issues(source: str, filename: str) -> list[tuple[str, int, str]]:
    ...

def main(argv: Sequence[str] | None = None) -> int:
    ...

# WRONG — no return type, no parameter types
def detect_issues(source, filename):
    ...
```

### Violation tuple convention

All hooks that return violations use:
```python
Violation = tuple[str, int, str]  # (filename, lineno, message)
```

---

## `main()` Signature (MANDATORY for all hooks)

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
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_something(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
```

---

## Pattern-Based Hooks

For simple regex-based detection, inherit `PatternDetection`:

```python
from pre_commit_hooks.tools.pattern_detection import PatternDetection

def main(argv: Sequence[str] | None = None) -> int:
    return PatternDetection(
        commented=re.compile(r'^\s*#\s*my_pattern'),
        disable_comment=re.compile(r'my-hook\s*:\s*disable'),
        pattern=re.compile(r'^\s*my_pattern'),
    ).detect(argv=argv)
```

---

## Disable Comment Convention

Each hook must support per-line suppression:

| Scope | Format |
|---|---|
| Python | `# hook-name: disable` |
| CSS | `/* hook-name: disable */` |
| JS/TS | `// hook-name: disable` |
| Dockerfile | `# hook-name: disable` |

---

## Imports

- Always sort: stdlib → third-party → local
- No `TYPE_CHECKING` guard (Python 3.12+ doesn't need it for most cases)
- Use `collections.abc` not `typing` for `Sequence`, `Iterator`, etc.

```python
# CORRECT
from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pattern_detection import PatternDetection
```

---

## Security (Ruff S rules)

- No `shell=True` in `subprocess` without `# noqa: S602` + justification comment
- No `open()` without `encoding='utf-8'`
- No hardcoded credentials — use `detect-secrets` pre-commit hook

---

## Error Handling

- Only validate at system boundaries (file I/O, user input)
- Use `(OSError, UnicodeDecodeError)` for file reads
- Never use bare `except:`

```python
# CORRECT
try:
    with open(filename, encoding='utf-8') as f:
        source = f.read()
except (OSError, UnicodeDecodeError):
    continue

# WRONG
try:
    source = open(filename).read()
except:
    pass
```

---

## Adding a New Hook — Checklist

1. Create `pre_commit_hooks/my_hook.py`
2. Add entry point in `setup.cfg` → `console_scripts`
3. Register in `.pre-commit-hooks.yaml`
4. Write tests in `tests/test_my_hook.py`
5. Run `ruff check` + `pytest` — both must pass
6. Add documentation in `README.md`
