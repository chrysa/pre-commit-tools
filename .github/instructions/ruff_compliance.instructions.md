---
applyTo: "**/*.py"
---

# Ruff Compliance Guidelines

## Ruff is the Sole Linting Authority

No flake8, pylint (for linting), black, or isort. Ruff replaces all of them.
Configuration: `config-tools/ruff.toml`

---

## Commands to Run Before Committing

```bash
# Check for violations
ruff check --config=config-tools/ruff.toml pre_commit_hooks tests

# Auto-fix safe violations
ruff check --config=config-tools/ruff.toml --fix pre_commit_hooks tests

# Format check (equivalent to black)
ruff format --check --config=config-tools/ruff.toml pre_commit_hooks

# Apply formatting
ruff format --config=config-tools/ruff.toml pre_commit_hooks
```

**All violations must be fixed before any commit. Zero tolerance.**

---

## Active Rule Sets

| Prefix | Category | Key rules enforced |
|---|---|---|
| `E` / `W` | pycodestyle | Line length, whitespace, syntax |
| `F` | Pyflakes | Unused imports, undefined names |
| `I` | isort | Import ordering |
| `N` | pep8-naming | Naming conventions |
| `UP` | pyupgrade | Modern Python syntax (PEP 585/604) |
| `B` | flake8-bugbear | Common bugs, opinionated style |
| `C90` | mccabe | Complexity |
| `ANN` | flake8-annotations | Missing type annotations |
| `S` | flake8-bandit | Security issues |
| `TID` | flake8-tidy-imports | Import tidiness |
| `PERF` | perflint | Performance anti-patterns |
| `FURB` | refurb | Code modernization |
| `RUF` | Ruff-specific | Ruff own rules (RUF059: unused vars) |
| `PLR` | Pylint refactor | Refactoring suggestions |

---

## `# noqa` Usage

Every `# noqa` suppression **must** include the rule code and a comment:

```python
# CORRECT
result: Any = external_lib.call()  # noqa: ANN401 — third-party untyped API

# WRONG — bare noqa without explanation
result = external_lib.call()  # noqa
```

---

## Common Violations to Avoid

```python
# ANN201 — missing return type
def get_items():  # WRONG
    return []

def get_items() -> list[str]:  # CORRECT
    return []

# UP006/UP007 — use built-in generics (PEP 585/604)
from typing import List, Optional  # WRONG
def f(x: Optional[str]) -> List[int]: ...

def f(x: str | None) -> list[int]: ...  # CORRECT

# RUF059 — unused unpacked variable (prefix with _)
a, b = some_function()  # WRONG if b unused
a, _b = some_function()  # CORRECT

# S603/S607 — subprocess
subprocess.run(['ls'])  # OK
subprocess.run('ls', shell=True)  # noqa: S602 — requires justification

# B006 — mutable default argument
def f(items=[]):  # WRONG
def f(items: list[str] | None = None):  # CORRECT
    items = items or []
```

---

## Pre-commit Integration

Ruff runs automatically via pre-commit:

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.15.8
  hooks:
    - id: ruff
      args: [--config=config-tools/ruff.toml, --fix]
    - id: ruff-format
      args: [--config=config-tools/ruff.toml]
```
