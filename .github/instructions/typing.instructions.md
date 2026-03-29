---
applyTo: "**/*.py"
---

# Typing Guidelines

## Core Principle

All public functions and methods must have **complete type annotations**.
Missing annotations are caught by Ruff `ANN` rules (treated as errors).

---

## Python Version

Target Python 3.12+. Use built-in generics everywhere (PEP 585, PEP 604):

```python
# CORRECT — Python 3.12+
from __future__ import annotations

def process(items: list[str]) -> dict[str, int]: ...
def lookup(key: str) -> str | None: ...

# WRONG — legacy typing module
from typing import Dict, List, Optional
def process(items: List[str]) -> Dict[str, int]: ...
def lookup(key: str) -> Optional[str]: ...
```

---

## Union Types (PEP 604)

```python
# CORRECT
def find(name: str, default: str | None = None) -> str | None: ...
def parse(value: str | int) -> float: ...

# WRONG
from typing import Optional, Union
def find(name: str, default: Optional[str] = None) -> Optional[str]: ...
def parse(value: Union[str, int]) -> float: ...
```

---

## Collections (PEP 585)

```python
# CORRECT — built-in generics
items: list[str]
mapping: dict[str, int]
pair: tuple[str, int]
group: set[str]
nested: list[dict[str, list[int]]]

# WRONG — typing module generics
from typing import Dict, List, Set, Tuple
items: List[str]
mapping: Dict[str, int]
```

---

## Abstract Types

Use `collections.abc` not `typing`:

```python
# CORRECT
from collections.abc import Callable, Iterator, Mapping, Sequence

def main(argv: Sequence[str] | None = None) -> int: ...
def transform(fn: Callable[[str], str]) -> list[str]: ...

# WRONG
from typing import Callable, Iterator, Mapping, Sequence
```

---

## No `Any`

Avoid `Any` unless absolutely unavoidable:

```python
# WRONG
from typing import Any
def handle(data: Any) -> Any: ...

# CORRECT — use specific types or overloads
def handle(data: dict[str, str | int | bool]) -> dict[str, str]: ...

# If Any is truly needed, document why
from typing import Any  # noqa: ANN401 — third-party API returns untyped result
result: Any = external_lib.get_result()
```

---

## Return Annotations

**Every function must have a return annotation**, including `-> None`:

```python
# CORRECT
def setup() -> None:
    ...

def count() -> int:
    return 42

# WRONG
def setup():
    ...
```

---

## `from __future__ import annotations`

Add to every Python file for forward references and to enable `|` union syntax
under Python 3.10/3.11 (for when callers run with older interpreters):

```python
from __future__ import annotations
```

---

## Violations (from this codebase)

| Ruff rule | What it catches |
|---|---|
| `ANN001` | Missing function argument annotation |
| `ANN002` | Missing `*args` annotation |
| `ANN003` | Missing `**kwargs` annotation |
| `ANN201` | Missing return type annotation (public) |
| `ANN202` | Missing return type annotation (private) |
| `ANN204` | Missing return type on `__init__` |

All are enabled in `config-tools/ruff.toml`.
