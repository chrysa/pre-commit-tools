---
applyTo: "tests/**/*.py"
---

# Testing Conventions

## File Organization

- One test file per hook: `tests/test_<hook_slug>.py`
- Import only the public API of the hook under test

## Required Imports

```python
from __future__ import annotations

from pathlib import Path
import pytest

from pre_commit_hooks.my_hook import main, my_function
```

## `_write()` Helper

Every test file that creates temporary CSS/TS/JS/Python files must define:

```python
def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)
```

## Class Structure (MANDATORY)

Group tests by function/scenario:

```python
class TestMyFunction:
    def test_clean_input_returns_empty(self) -> None: ...
    def test_violation_detected(self) -> None: ...
    def test_disable_comment_suppresses(self) -> None: ...

class TestMyHookMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None: ...
    def test_violation_returns_1(self, tmp_path: Path) -> None: ...
    def test_empty_args_returns_0(self) -> None: ...
```

## String Content in Tests

Always use `\n` escape sequences — NEVER literal newlines:

```python
# CORRECT
css = '.foo {\n  color: red;\n}\n'

# WRONG — breaks ruff and causes syntax errors
css = '''.foo {
  color: red;
}
'''
```

## `@pytest.mark.parametrize` Usage

Use parametrize for multiple inputs to the same function:

```python
@pytest.mark.parametrize('source,expected', [
    ('clean code', []),
    ('print("x")', [('f.py', 1, 'print detected')]),
])
def test_detect(source: str, expected: list) -> None:
    assert detect(source, 'f.py') == expected
```

## Skipping Optional Dependencies

For hooks with optional deps (tree-sitter, etc.):

```python
tree_sitter = pytest.importorskip('tree_sitter', reason='tree-sitter not installed')
tree_sitter_typescript = pytest.importorskip('tree_sitter_typescript', reason='tree-sitter-typescript not installed')

# Then import the hook AFTER the skip
from pre_commit_hooks.ts_unreachable_code_detection import main  # noqa: E402
```

## Unused Variables in Unpacking

Prefix unused unpacked variables with `_` to satisfy ruff RUF059:

```python
fname, _lineno, msg = violations[0]
_changed, result = sort_function(content)
```

## Return Value Conventions

- `main([]) == 0` — no files → no error
- `main(['clean.py']) == 0` — clean file → exit 0
- `main(['bad.py']) == 1` — violation found → exit 1
