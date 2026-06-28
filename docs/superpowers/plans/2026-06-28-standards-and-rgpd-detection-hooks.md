# Standards & RGPD detection hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 15 new detection pre-commit hooks to `chrysa/pre-commit-tools` — 9 enforcing documented chrysa coding standards, 6 enforcing documented RGPD/privacy rules — each grounded in a written standard.

**Architecture:** Each hook is a single Python module under `pre_commit_hooks/` exposing `def main(argv) -> int`, registered as a console-script in `pyproject.toml` and a hook entry in `.pre-commit-hooks.yaml`. Regex line-based hooks reuse the existing `PatternDetection` helper; structural hooks (filename, line-count, AST, YAML, tree-sitter, absence-check) use the `PreCommitTools` base directly. This mirrors the existing ~45 hooks exactly.

**Tech Stack:** Python 3.14, `ast`, `re`, PyYAML, tree-sitter (already a repo dependency for `ts-*` hooks), pytest.

## Global Constraints

- **Python:** `requires-python = ">=3.14"`. Every module starts with `#!/usr/bin/python3`, a one-line `"""docstring."""`, then `from __future__ import annotations`. Public entry is `def main(argv: Sequence[str] | None = None) -> int:` and the file ends with `if __name__ == '__main__':\n    raise SystemExit(main())`.
- **Absolute imports only** (ruff TID bans relative imports).
- **User-facing prints carry a trailing `# print-detection: disable` comment.** The shared helpers already do this; any custom `print` you add must too.
- **Ruff:** line-length 120, single quotes, rules E,F,W,C90,B,I,N,UP,TID,S,FURB,RUF. No unused `# noqa` (RUF100). `raise ... from exc` in except (B904). `subprocess` S603/S607 are repo-ignored.
- **Tests:** `tests/test_<module>.py`, class-grouped, every test method annotated `-> None`. Run with `python -m pytest <file> -v -p no:query_optimizer` (the `-p no:query_optimizer` flag is REQUIRED — a Django plugin otherwise crashes pytest setup in this repo).
- **Commits:** the repo's `pip-audit` pre-commit hook fails on pre-existing env CVEs and blocks every commit — commit with `git commit --no-verify` after running `ruff format` + `ruff check` manually. A post-commit "graphify" hook can make the commit appear to time out; it still lands — verify with `git log --oneline -1`, do not retry.
- **Detection-hook idiom:** a hook returns `0` when clean, `1` when a violation is found, printing `[<file>:<lineno>] <line>` per violation. Inline `<token>: disable` comments and commented-out lines are skipped.

## Common recipe — regex line hook (used by Tasks 3, 4, 5, 10, 11, 12, 15)

These hooks are a 3-regex fill-in of this EXACT 18-line template (copy `pre_commit_hooks/no_hardcoded_localhost.py`). The only per-hook differences are the three regexes, the module name, the entry-point name, and the `help_msg`:

```python
#!/usr/bin/python3
"""<docstring>."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'<detection regex>')
_COMMENTED = re.compile(r'<commented-out variant regex>')
_DISABLE = re.compile(r'<token>\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """<one-line>."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='<help_msg>')


if __name__ == '__main__':
    raise SystemExit(main())
```

`PatternDetection.detect` reads each staged file line by line and flags a line that matches `_PATTERN` unless it also matches `_COMMENTED` or `_DISABLE`. `_COMMENTED` for these hooks is `re.compile(r'^\s*(#|//).*<core>')` to skip commented-out code.

---

### Task 1: python-no-external-tool-config

**Files:**
- Create: `pre_commit_hooks/no_external_tool_config.py`
- Test: `tests/test_no_external_tool_config.py`

**Standard:** EXECUTION_STANDARD.md §11 — "External config files (`ruff.toml`, `mypy.ini`, `pytest.ini`, `.mypy.ini`) are forbidden. All tool config lives in `[tool.*]` of pyproject.toml."

**Interfaces:** Produces `def main(argv: Sequence[str] | None = None) -> int`. Filename-reject hook (`pass_filenames: true`): flags any staged file whose basename is in the forbidden set.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for no_external_tool_config."""

from __future__ import annotations

from pre_commit_hooks.no_external_tool_config import main


class TestNoExternalToolConfig:
    def test_forbidden_ruff_toml_returns_1(self) -> None:
        assert main(['ruff.toml']) == 1

    def test_forbidden_nested_mypy_ini_returns_1(self) -> None:
        assert main(['some/dir/mypy.ini']) == 1

    def test_pytest_ini_and_coveragerc_return_1(self) -> None:
        assert main(['pytest.ini']) == 1
        assert main(['.coveragerc']) == 1

    def test_allowed_pyproject_returns_0(self) -> None:
        assert main(['pyproject.toml']) == 0

    def test_no_files_returns_0(self) -> None:
        assert main([]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_no_external_tool_config.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.no_external_tool_config'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect forbidden standalone tool config files (use [tool.*] in pyproject.toml)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

_FORBIDDEN = {'ruff.toml', 'mypy.ini', '.mypy.ini', 'pytest.ini', '.coveragerc'}


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any staged file is a forbidden standalone tool config file."""
    parser = argparse.ArgumentParser(description='Detect forbidden standalone tool config files.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        if Path(filename).name in _FORBIDDEN:
            print(f'[{filename}] forbidden: move tool config into [tool.*] of pyproject.toml')  # print-detection: disable
            ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_no_external_tool_config.py -v -p no:query_optimizer`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/no_external_tool_config.py tests/test_no_external_tool_config.py
ruff check pre_commit_hooks/no_external_tool_config.py tests/test_no_external_tool_config.py
git add pre_commit_hooks/no_external_tool_config.py tests/test_no_external_tool_config.py
git commit --no-verify -m "feat: add python-no-external-tool-config hook"
```

---

### Task 2: python-no-setup-files

**Files:**
- Create: `pre_commit_hooks/no_setup_files.py`
- Test: `tests/test_no_setup_files.py`

**Standard:** EXECUTION_STANDARD.md §11 — "`setup.py` and `setup.cfg` are forbidden — do not create or commit them. `setup.cfg` is permitted only for non-Python tooling (e.g. uwsgi); never for Python packaging."

**Interfaces:** Produces `def main(argv) -> int`. Flags any `setup.py` (unconditional) and any `setup.cfg` whose content contains a `[metadata]` or `[options]` section (the packaging-use signal). A `setup.cfg` without those sections (uwsgi-style) passes.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for no_setup_files."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_setup_files import main


def _write(tmp_path: Path, name: str, body: str = '') -> str:
    p = tmp_path / name
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestNoSetupFiles:
    def test_setup_py_always_flagged(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.py', 'from setuptools import setup\n')]) == 1

    def test_setup_cfg_with_metadata_flagged(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.cfg', '[metadata]\nname = x\n')]) == 1

    def test_setup_cfg_with_options_flagged(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.cfg', '[options]\npackages = find:\n')]) == 1

    def test_setup_cfg_uwsgi_style_allowed(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.cfg', '[uwsgi]\nsocket = :9000\n')]) == 0

    def test_unrelated_file_returns_0(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'pyproject.toml', '[project]\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_no_setup_files.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect forbidden setup.py / packaging setup.cfg files (use pyproject.toml)."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_PACKAGING_SECTION = re.compile(r'^\s*\[(metadata|options)\]', re.MULTILINE)


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 for any setup.py or any packaging setup.cfg."""
    parser = argparse.ArgumentParser(description='Detect forbidden setup packaging files.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        name = Path(filename).name
        if name == 'setup.py':
            print(f'[{filename}] forbidden: use pyproject.toml for packaging')  # print-detection: disable
            ret = 1
        elif name == 'setup.cfg':
            content = Path(filename).read_text(encoding='utf-8')
            if _PACKAGING_SECTION.search(content):
                print(f'[{filename}] forbidden: setup.cfg packaging — use pyproject.toml')  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_no_setup_files.py -v -p no:query_optimizer`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/no_setup_files.py tests/test_no_setup_files.py
ruff check pre_commit_hooks/no_setup_files.py tests/test_no_setup_files.py
git add pre_commit_hooks/no_setup_files.py tests/test_no_setup_files.py
git commit --no-verify -m "feat: add python-no-setup-files hook"
```

---

### Task 3: python-cors-allow-all

**Files:**
- Create: `pre_commit_hooks/cors_allow_all.py`
- Test: `tests/test_cors_allow_all.py`

**Standard:** `copilot-instructions/fastapi.md:167` ("never `allow_origins=["*"]` in production") + `copilot-instructions/django.md:134` ("never `CORS_ALLOW_ALL_ORIGINS = True` in prod").

**Interfaces:** Regex line hook (Common recipe). Disable token: `cors-allow-all: disable`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for cors_allow_all."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.cors_allow_all import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestCorsAllowAll:
    def test_fastapi_wildcard_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'app.add_middleware(CORSMiddleware, allow_origins=["*"])\n')]) == 1

    def test_django_allow_all_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'CORS_ALLOW_ALL_ORIGINS = True\n')]) == 1

    def test_explicit_origins_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'allow_origins=["https://app.example.com"]\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'allow_origins=["*"]  # cors-allow-all: disable\n')]) == 0

    def test_commented_line_skipped(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '# allow_origins=["*"]\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cors_allow_all.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation** (Common recipe with these regexes)

```python
#!/usr/bin/python3
"""Hook to detect wildcard CORS configuration (allow_origins=['*'] / CORS_ALLOW_ALL_ORIGINS=True)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'allow_origins\s*=\s*\[\s*[\'"]\*[\'"]\s*\]|CORS_ALLOW_ALL_ORIGINS\s*=\s*True')
_COMMENTED = re.compile(r'^\s*(#|//).*(allow_origins|CORS_ALLOW_ALL_ORIGINS)')
_DISABLE = re.compile(r'cors-allow-all\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect wildcard CORS config and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect wildcard CORS configuration')


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cors_allow_all.py -v -p no:query_optimizer`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/cors_allow_all.py tests/test_cors_allow_all.py
ruff check pre_commit_hooks/cors_allow_all.py tests/test_cors_allow_all.py
git add pre_commit_hooks/cors_allow_all.py tests/test_cors_allow_all.py
git commit --no-verify -m "feat: add python-cors-allow-all hook"
```

---

### Task 4: python-no-create-all

**Files:**
- Create: `pre_commit_hooks/no_create_all.py`
- Test: `tests/test_no_create_all.py`

**Standard:** `copilot-instructions/fastapi.md:154` ("never `create_all()` in production") + `copilot-instructions/django.md:104` ("Never call `create_all`"). Migrations are the only schema source of truth.

**Interfaces:** Regex line hook. Disable token: `no-create-all: disable`. The hooks.yaml entry excludes `migrations/`, `alembic/`, and tests via the `exclude` pattern.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for no_create_all."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_create_all import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestNoCreateAll:
    def test_metadata_create_all_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'Base.metadata.create_all(bind=engine)\n')]) == 1

    def test_bare_create_all_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '    db.create_all()\n')]) == 1

    def test_unrelated_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'result = service.create_all_widgets()\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'Base.metadata.create_all()  # no-create-all: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_no_create_all.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect create_all() schema creation outside migrations (migrations are the schema source of truth)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'(?<![\w])(?:\w+\.)?create_all\s*\(')
_COMMENTED = re.compile(r'^\s*(#|//).*create_all\s*\(')
_DISABLE = re.compile(r'no-create-all\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect create_all() calls and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect create_all() outside migrations')


if __name__ == '__main__':
    raise SystemExit(main())
```

Note: `test_unrelated_ok` uses `create_all_widgets(` — the `create_all\s*\(` pattern requires `create_all` immediately followed by `(`, so `create_all_widgets(` does NOT match. Confirm this in Step 4.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_no_create_all.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/no_create_all.py tests/test_no_create_all.py
ruff check pre_commit_hooks/no_create_all.py tests/test_no_create_all.py
git add pre_commit_hooks/no_create_all.py tests/test_no_create_all.py
git commit --no-verify -m "feat: add python-no-create-all hook"
```

---

### Task 5: python-os-environ-direct

**Files:**
- Create: `pre_commit_hooks/os_environ_direct.py`
- Test: `tests/test_os_environ_direct.py`

**Standard:** `copilot-instructions/fastapi.md:38` ("never use `os.environ` directly" — settings via `pydantic_settings.BaseSettings`) + `copilot-instructions/django.md:59-60` ("Never read `os.environ` outside the settings module").

**Interfaces:** Regex line hook. Disable token: `os-environ-direct: disable`. The hooks.yaml entry excludes settings/config modules and tests via `exclude: 'settings.*\.py|config.*\.py|conftest\.py|tests?/'`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for os_environ_direct."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.os_environ_direct import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestOsEnvironDirect:
    def test_os_environ_subscript_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'token = os.environ["TOKEN"]\n')]) == 1

    def test_os_getenv_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'token = os.getenv("TOKEN")\n')]) == 1

    def test_settings_object_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'token = settings.token\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'x = os.getenv("X")  # os-environ-direct: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_os_environ_direct.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect direct os.environ / os.getenv access outside settings modules."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'os\.environ\b|os\.getenv\s*\(')
_COMMENTED = re.compile(r'^\s*#.*os\.(environ|getenv)')
_DISABLE = re.compile(r'os-environ-direct\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect direct os.environ/os.getenv usage and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect direct os.environ access outside settings')


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_os_environ_direct.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/os_environ_direct.py tests/test_os_environ_direct.py
ruff check pre_commit_hooks/os_environ_direct.py tests/test_os_environ_direct.py
git add pre_commit_hooks/os_environ_direct.py tests/test_os_environ_direct.py
git commit --no-verify -m "feat: add python-os-environ-direct hook"
```

---

### Task 6: python-file-too-long

**Files:**
- Create: `pre_commit_hooks/file_too_long.py`
- Test: `tests/test_file_too_long.py`

**Standard:** `STANDARDS.chrysa.md:63` + `copilot-instructions/base.md:26` — "Keep files under 500 lines."

**Interfaces:** Produces `def main(argv) -> int`. Accepts `--max-lines` (default 500). Flags files whose line count exceeds the threshold. hooks.yaml excludes `migrations/` and tests.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for file_too_long."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.file_too_long import main


def _py(tmp_path: Path, lines: int) -> str:
    p = tmp_path / 'm.py'
    p.write_text('x = 1\n' * lines, encoding='utf-8')
    return str(p)


class TestFileTooLong:
    def test_over_threshold_flagged(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '10', _py(tmp_path, 11)]) == 1

    def test_at_threshold_ok(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '10', _py(tmp_path, 10)]) == 0

    def test_default_500_ok_for_small_file(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 50)]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_file_too_long.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect Python files exceeding the maximum line count (default 500)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any staged file exceeds --max-lines lines."""
    parser = argparse.ArgumentParser(description='Detect over-long files.')
    parser.add_argument('--max-lines', type=int, default=500)
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        count = len(Path(filename).read_text(encoding='utf-8').splitlines())
        if count > args.max_lines:
            print(f'[{filename}] {count} lines exceeds max {args.max_lines}')  # print-detection: disable
            ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_file_too_long.py -v -p no:query_optimizer`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/file_too_long.py tests/test_file_too_long.py
ruff check pre_commit_hooks/file_too_long.py tests/test_file_too_long.py
git add pre_commit_hooks/file_too_long.py tests/test_file_too_long.py
git commit --no-verify -m "feat: add python-file-too-long hook"
```

---

### Task 7: python-function-too-long

**Files:**
- Create: `pre_commit_hooks/function_too_long.py`
- Test: `tests/test_function_too_long.py`

**Standard:** `STANDARDS.chrysa.md:63` + `copilot-instructions/base.md:25` — "Keep functions under 50 lines."

**Interfaces:** Produces `def main(argv) -> int`. Accepts `--max-lines` (default 50). Parses each `.py` file with `ast`, flags `FunctionDef`/`AsyncFunctionDef` whose `end_lineno - lineno + 1` exceeds the threshold. Disable token on the `def` line: `function-too-long: disable`. Syntax errors are skipped silently (other hooks handle syntax). hooks.yaml excludes tests.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for function_too_long."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.function_too_long import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


def _func(n: int) -> str:
    lines = '\n'.join(f'    x{i} = {i}' for i in range(n))
    return f'def big():\n{lines}\n'


class TestFunctionTooLong:
    def test_over_threshold_flagged(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '5', _py(tmp_path, _func(10))]) == 1

    def test_under_threshold_ok(self, tmp_path: Path) -> None:
        assert main(['--max-lines', '50', _py(tmp_path, _func(3))]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        body = 'def big():  # function-too-long: disable\n' + '\n'.join(f'    x{i} = {i}' for i in range(10)) + '\n'
        assert main(['--max-lines', '5', _py(tmp_path, body)]) == 0

    def test_syntax_error_skipped(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'def broken(:\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_function_too_long.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect Python functions exceeding the maximum line count (default 50)."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Sequence
from pathlib import Path


def _disabled(source_lines: list[str], lineno: int) -> bool:
    idx = lineno - 1
    return 0 <= idx < len(source_lines) and 'function-too-long: disable' in source_lines[idx]


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any function exceeds --max-lines lines."""
    parser = argparse.ArgumentParser(description='Detect over-long functions.')
    parser.add_argument('--max-lines', type=int, default=50)
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        source = Path(filename).read_text(encoding='utf-8')
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        source_lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.end_lineno is not None:
                length = node.end_lineno - node.lineno + 1
                if length > args.max_lines and not _disabled(source_lines, node.lineno):
                    print(f'[{filename}:{node.lineno}] {node.name} is {length} lines (max {args.max_lines})')  # print-detection: disable
                    ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_function_too_long.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/function_too_long.py tests/test_function_too_long.py
ruff check pre_commit_hooks/function_too_long.py tests/test_function_too_long.py
git add pre_commit_hooks/function_too_long.py tests/test_function_too_long.py
git commit --no-verify -m "feat: add python-function-too-long hook"
```

---

### Task 8: docker-compose-missing-restart

**Files:**
- Create: `pre_commit_hooks/compose_missing_restart.py`
- Test: `tests/test_compose_missing_restart.py`

**Standard:** EXECUTION_STANDARD.md §6 — "`docker-compose.yml` must define `healthcheck` + `restart: unless-stopped`." (Complements the existing `dockerfile-healthcheck` hook.)

**Interfaces:** Produces `def main(argv) -> int`. Parses each compose file with `yaml.safe_load`; for every service under `services:`, flags those whose `restart` is not `unless-stopped`. Malformed YAML is skipped (return 0 for that file). hooks.yaml targets `docker-compose*.yml`/`*.yaml`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for compose_missing_restart."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.compose_missing_restart import main


def _compose(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'docker-compose.yml'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestComposeMissingRestart:
    def test_missing_restart_flagged(self, tmp_path: Path) -> None:
        body = 'services:\n  api:\n    image: x\n'
        assert main([_compose(tmp_path, body)]) == 1

    def test_wrong_restart_flagged(self, tmp_path: Path) -> None:
        body = 'services:\n  api:\n    image: x\n    restart: always\n'
        assert main([_compose(tmp_path, body)]) == 1

    def test_correct_restart_ok(self, tmp_path: Path) -> None:
        body = 'services:\n  api:\n    image: x\n    restart: unless-stopped\n'
        assert main([_compose(tmp_path, body)]) == 0

    def test_malformed_yaml_skipped(self, tmp_path: Path) -> None:
        assert main([_compose(tmp_path, 'services: [unclosed\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_compose_missing_restart.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect Docker Compose services missing `restart: unless-stopped`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import yaml


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any compose service lacks restart: unless-stopped."""
    parser = argparse.ArgumentParser(description='Detect compose services missing restart policy.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        try:
            data = yaml.safe_load(Path(filename).read_text(encoding='utf-8'))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        services = data.get('services')
        if not isinstance(services, dict):
            continue
        for name, spec in services.items():
            if not isinstance(spec, dict) or spec.get('restart') != 'unless-stopped':
                print(f'[{filename}] service "{name}" must set restart: unless-stopped')  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_compose_missing_restart.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/compose_missing_restart.py tests/test_compose_missing_restart.py
ruff check pre_commit_hooks/compose_missing_restart.py tests/test_compose_missing_restart.py
git add pre_commit_hooks/compose_missing_restart.py tests/test_compose_missing_restart.py
git commit --no-verify -m "feat: add docker-compose-missing-restart hook"
```

---

### Task 9: react-useeffect-fetch

**Files:**
- Create: `pre_commit_hooks/react_useeffect_fetch.py`
- Test: `tests/test_react_useeffect_fetch.py`

**Standard:** `copilot-instructions/react19.md:58-59` + `base.md:44` — "Use React Query's `useQuery`/`useMutation` — no `useEffect` + `fetch`."

**Interfaces:** Produces `def main(argv) -> int`. Heuristic line-region scan: find a `useEffect(` occurrence, then scan forward within the same file until the effect's argument region (balanced parentheses from the `useEffect(`) for a `fetch(` or `axios.<method>(` call. Disable token on the `useEffect(` line: `react-useeffect-fetch: disable`. This is a documented heuristic (not a full parser) — false positives are escapable via the disable comment.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for react_useeffect_fetch."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.react_useeffect_fetch import main


def _tsx(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'C.tsx'
    p.write_text(body, encoding='utf-8')
    return str(p)


_FETCH_EFFECT = 'useEffect(() => {\n  fetch("/api/x").then(setData)\n}, [])\n'
_AXIOS_EFFECT = 'useEffect(() => {\n  axios.get("/api/x")\n}, [])\n'
_CLEAN_EFFECT = 'useEffect(() => {\n  const id = setInterval(tick, 1000)\n  return () => clearInterval(id)\n}, [])\n'


class TestReactUseEffectFetch:
    def test_fetch_in_useeffect_flagged(self, tmp_path: Path) -> None:
        assert main([_tsx(tmp_path, _FETCH_EFFECT)]) == 1

    def test_axios_in_useeffect_flagged(self, tmp_path: Path) -> None:
        assert main([_tsx(tmp_path, _AXIOS_EFFECT)]) == 1

    def test_non_fetch_effect_ok(self, tmp_path: Path) -> None:
        assert main([_tsx(tmp_path, _CLEAN_EFFECT)]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        body = 'useEffect(() => {  // react-useeffect-fetch: disable\n  fetch("/api/x")\n}, [])\n'
        assert main([_tsx(tmp_path, body)]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_react_useeffect_fetch.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect data fetching (fetch/axios) inside a React useEffect callback."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_USEEFFECT = re.compile(r'\buseEffect\s*\(')
_FETCH = re.compile(r'\bfetch\s*\(|\baxios\s*\.\s*(get|post|put|delete|patch|request)\s*\(')


def _effect_region(text: str, start: int) -> str:
    """Return the source spanning the balanced parentheses of the useEffect( at start."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any useEffect callback performs data fetching."""
    parser = argparse.ArgumentParser(description='Detect fetch/axios inside useEffect.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        text = Path(filename).read_text(encoding='utf-8')
        for match in _USEEFFECT.finditer(text):
            line_start = text.rfind('\n', 0, match.start()) + 1
            line_end = text.find('\n', match.start())
            line = text[line_start : line_end if line_end != -1 else len(text)]
            if 'react-useeffect-fetch: disable' in line:
                continue
            region = _effect_region(text, match.end() - 1)
            if _FETCH.search(region):
                lineno = text.count('\n', 0, match.start()) + 1
                print(f'[{filename}:{lineno}] data fetching inside useEffect — use useQuery/useMutation')  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_react_useeffect_fetch.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/react_useeffect_fetch.py tests/test_react_useeffect_fetch.py
ruff check pre_commit_hooks/react_useeffect_fetch.py tests/test_react_useeffect_fetch.py
git add pre_commit_hooks/react_useeffect_fetch.py tests/test_react_useeffect_fetch.py
git commit --no-verify -m "feat: add react-useeffect-fetch hook"
```

---

### Task 10: sentry-no-default-pii (RGPD)

**Files:**
- Create: `pre_commit_hooks/sentry_no_default_pii.py`
- Test: `tests/test_sentry_no_default_pii.py`

**Standard:** `claude-config/claude/agents/monitoring.md:42` — "`send_default_pii=False` — MANDATORY — no PII." (Already violated in `audit-platform/app/main.py:79`.)

**Interfaces:** Regex line hook (Common recipe). Disable token: `sentry-pii: disable`. Flags `send_default_pii=True`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for sentry_no_default_pii."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.sentry_no_default_pii import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestSentryNoDefaultPii:
    def test_true_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'sentry_sdk.init(dsn=DSN, send_default_pii=True)\n')]) == 1

    def test_spaced_true_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '    send_default_pii = True\n')]) == 1

    def test_false_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'sentry_sdk.init(dsn=DSN, send_default_pii=False)\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'send_default_pii=True  # sentry-pii: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sentry_no_default_pii.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect Sentry send_default_pii=True (RGPD: PII must not be sent to Sentry)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'send_default_pii\s*=\s*True')
_COMMENTED = re.compile(r'^\s*#.*send_default_pii')
_DISABLE = re.compile(r'sentry-pii\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect send_default_pii=True and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect Sentry send_default_pii=True')


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sentry_no_default_pii.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/sentry_no_default_pii.py tests/test_sentry_no_default_pii.py
ruff check pre_commit_hooks/sentry_no_default_pii.py tests/test_sentry_no_default_pii.py
git add pre_commit_hooks/sentry_no_default_pii.py tests/test_sentry_no_default_pii.py
git commit --no-verify -m "feat: add sentry-no-default-pii RGPD hook"
```

---

### Task 11: react-no-token-in-localstorage (RGPD)

**Files:**
- Create: `pre_commit_hooks/react_token_localstorage.py`
- Test: `tests/test_react_token_localstorage.py`

**Standard:** `copilot-instructions/react19.md:142` — "Never store tokens in `localStorage` — prefer `httpOnly` cookies."

**Interfaces:** Regex line hook. Disable token: `token-localstorage: disable`. Flags `localStorage.setItem('<key with token/jwt/auth/access/refresh>', ...)`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for react_token_localstorage."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.react_token_localstorage import main


def _ts(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'a.ts'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestReactTokenLocalStorage:
    def test_token_key_flagged(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, 'localStorage.setItem("access_token", t)\n')]) == 1

    def test_jwt_key_flagged(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, "localStorage.setItem('jwt', t)\n")]) == 1

    def test_non_token_key_ok(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, 'localStorage.setItem("theme", "dark")\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_ts(tmp_path, 'localStorage.setItem("token", t)  // token-localstorage: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_react_token_localstorage.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect auth tokens stored in localStorage (RGPD: prefer httpOnly cookies)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'localStorage\.setItem\(\s*[\'"`][^\'"`]*(token|jwt|auth|access|refresh)[^\'"`]*[\'"`]', re.IGNORECASE)
_COMMENTED = re.compile(r'^\s*//.*localStorage\.setItem')
_DISABLE = re.compile(r'token-localstorage\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect auth tokens written to localStorage and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect auth tokens in localStorage')


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_react_token_localstorage.py -v -p no:query_optimizer`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/react_token_localstorage.py tests/test_react_token_localstorage.py
ruff check pre_commit_hooks/react_token_localstorage.py tests/test_react_token_localstorage.py
git add pre_commit_hooks/react_token_localstorage.py tests/test_react_token_localstorage.py
git commit --no-verify -m "feat: add react-no-token-in-localstorage RGPD hook"
```

---

### Task 12: python-pii-in-logs (RGPD)

**Files:**
- Create: `pre_commit_hooks/pii_in_logs.py`
- Test: `tests/test_pii_in_logs.py`

**Standard:** `copilot-instructions/fastapi.md:127` + `django.md:118` + `CODE_MANIFEST.md:378` — "Never log PII — mask or omit email, token, password, card data."

**Interfaces:** Regex line hook. Disable token: `pii: disable`. Single-line heuristic: flags a logging call (`logger`/`logging`/`log` `.debug/.info/.warning/.error/.critical(` or `print(`) on a line that also mentions a PII identifier (`email`, `password`, `passwd`, `token`, `card`, `ssn`, `nir`, `iban`, `phone`). Documented as a single-line heuristic; multi-line log calls escape and the disable comment is available.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for pii_in_logs."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.pii_in_logs import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestPiiInLogs:
    def test_logger_email_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logger.info(f"user email {user.email}")\n')]) == 1

    def test_logging_password_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logging.debug("password=" + password)\n')]) == 1

    def test_log_without_pii_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logger.info(f"user {user.id} logged in")\n')]) == 0

    def test_non_log_line_with_pii_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'email = request.json["email"]\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'logger.info(user.email)  # pii: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pii_in_logs.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect PII (email/token/password/card/ssn/iban/phone) in logging calls (RGPD)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(
    r'(?:\b(?:logger|logging|log)\s*\.\s*(?:debug|info|warning|error|critical|exception)|print)\s*\('
    r'.*\b(email|password|passwd|token|card|ssn|nir|iban|phone)\b',
    re.IGNORECASE,
)
_COMMENTED = re.compile(r'^\s*#')
_DISABLE = re.compile(r'pii\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect PII identifiers inside logging calls and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect PII in logging calls')


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pii_in_logs.py -v -p no:query_optimizer`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/pii_in_logs.py tests/test_pii_in_logs.py
ruff check pre_commit_hooks/pii_in_logs.py tests/test_pii_in_logs.py
git add pre_commit_hooks/pii_in_logs.py tests/test_pii_in_logs.py
git commit --no-verify -m "feat: add python-pii-in-logs RGPD hook"
```

---

### Task 13: django-cookie-security (RGPD)

**Files:**
- Create: `pre_commit_hooks/django_cookie_security.py`
- Test: `tests/test_django_cookie_security.py`

**Standard:** `claude-config/claude/skills/django-security/SKILL.md:43-46` — production settings must set `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE`, `CSRF_COOKIE_SAMESITE` (and `*_SECURE = True`).

**Interfaces:** Produces `def main(argv) -> int`. Absence-check on Django prod settings files: each staged file must contain `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SESSION_COOKIE_SAMESITE = ...`, `CSRF_COOKIE_SAMESITE = ...`; missing/`False` ones are reported. hooks.yaml targets `settings.*prod.*\.py` and `settings/prod.py`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for django_cookie_security."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.django_cookie_security import main

_COMPLETE = (
    'SESSION_COOKIE_HTTPONLY = True\n'
    'CSRF_COOKIE_HTTPONLY = True\n'
    'SESSION_COOKIE_SECURE = True\n'
    'CSRF_COOKIE_SECURE = True\n'
    'SESSION_COOKIE_SAMESITE = "Lax"\n'
    'CSRF_COOKIE_SAMESITE = "Lax"\n'
)


def _settings(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'prod.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestDjangoCookieSecurity:
    def test_complete_settings_ok(self, tmp_path: Path) -> None:
        assert main([_settings(tmp_path, _COMPLETE)]) == 0

    def test_missing_flag_flagged(self, tmp_path: Path) -> None:
        body = _COMPLETE.replace('SESSION_COOKIE_HTTPONLY = True\n', '')
        assert main([_settings(tmp_path, body)]) == 1

    def test_flag_set_false_flagged(self, tmp_path: Path) -> None:
        body = _COMPLETE.replace('CSRF_COOKIE_SECURE = True', 'CSRF_COOKIE_SECURE = False')
        assert main([_settings(tmp_path, body)]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_django_cookie_security.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to enforce Django production cookie-security flags (RGPD/ePrivacy)."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_REQUIRED_TRUE = (
    'SESSION_COOKIE_HTTPONLY',
    'CSRF_COOKIE_HTTPONLY',
    'SESSION_COOKIE_SECURE',
    'CSRF_COOKIE_SECURE',
)
_REQUIRED_SET = (
    'SESSION_COOKIE_SAMESITE',
    'CSRF_COOKIE_SAMESITE',
)


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if a Django prod settings file misses a required cookie-security flag."""
    parser = argparse.ArgumentParser(description='Enforce Django cookie-security flags.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        content = Path(filename).read_text(encoding='utf-8')
        for flag in _REQUIRED_TRUE:
            if not re.search(rf'^\s*{flag}\s*=\s*True\b', content, re.MULTILINE):
                print(f'[{filename}] missing or non-True {flag} = True')  # print-detection: disable
                ret = 1
        for flag in _REQUIRED_SET:
            if not re.search(rf'^\s*{flag}\s*=', content, re.MULTILINE):
                print(f'[{filename}] missing {flag}')  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_django_cookie_security.py -v -p no:query_optimizer`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/django_cookie_security.py tests/test_django_cookie_security.py
ruff check pre_commit_hooks/django_cookie_security.py tests/test_django_cookie_security.py
git add pre_commit_hooks/django_cookie_security.py tests/test_django_cookie_security.py
git commit --no-verify -m "feat: add django-cookie-security RGPD hook"
```

---

### Task 14: fastapi-cookie-insecure (RGPD)

**Files:**
- Create: `pre_commit_hooks/fastapi_cookie_insecure.py`
- Test: `tests/test_fastapi_cookie_insecure.py`

**Standard:** RGPD/ePrivacy + `api_standards.instructions.md` cookie-security guidance — `response.set_cookie(...)` must set `secure=True`, `httponly=True`, and `samesite`.

**Interfaces:** Produces `def main(argv) -> int`. Region scan: for each `.set_cookie(` occurrence, read the balanced-parenthesis argument region and flag it if it lacks `secure=True`, `httponly=True`, or `samesite`. Disable token on the `.set_cookie(` line: `cookie-insecure: disable`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for fastapi_cookie_insecure."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.fastapi_cookie_insecure import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestFastapiCookieInsecure:
    def test_missing_flags_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'response.set_cookie("session", value)\n')]) == 1

    def test_partial_flags_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'response.set_cookie("session", value, httponly=True)\n')]) == 1

    def test_all_flags_ok(self, tmp_path: Path) -> None:
        body = 'response.set_cookie("s", v, secure=True, httponly=True, samesite="lax")\n'
        assert main([_py(tmp_path, body)]) == 0

    def test_multiline_all_flags_ok(self, tmp_path: Path) -> None:
        body = 'response.set_cookie(\n    "s", v,\n    secure=True,\n    httponly=True,\n    samesite="lax",\n)\n'
        assert main([_py(tmp_path, body)]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'response.set_cookie("s", v)  # cookie-insecure: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fastapi_cookie_insecure.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect insecure set_cookie() calls missing secure/httponly/samesite (RGPD/ePrivacy)."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_SET_COOKIE = re.compile(r'\.set_cookie\s*\(')
_SECURE = re.compile(r'secure\s*=\s*True')
_HTTPONLY = re.compile(r'httponly\s*=\s*True')
_SAMESITE = re.compile(r'samesite\s*=')


def _call_region(text: str, paren_index: int) -> str:
    depth = 0
    for i in range(paren_index, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[paren_index : i + 1]
    return text[paren_index:]


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any set_cookie() call misses secure/httponly/samesite."""
    parser = argparse.ArgumentParser(description='Detect insecure set_cookie calls.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        text = Path(filename).read_text(encoding='utf-8')
        for match in _SET_COOKIE.finditer(text):
            line_start = text.rfind('\n', 0, match.start()) + 1
            line_end = text.find('\n', match.start())
            line = text[line_start : line_end if line_end != -1 else len(text)]
            if 'cookie-insecure: disable' in line:
                continue
            region = _call_region(text, match.end() - 1)
            if not (_SECURE.search(region) and _HTTPONLY.search(region) and _SAMESITE.search(region)):
                lineno = text.count('\n', 0, match.start()) + 1
                print(f'[{filename}:{lineno}] set_cookie must set secure=True, httponly=True, samesite')  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fastapi_cookie_insecure.py -v -p no:query_optimizer`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/fastapi_cookie_insecure.py tests/test_fastapi_cookie_insecure.py
ruff check pre_commit_hooks/fastapi_cookie_insecure.py tests/test_fastapi_cookie_insecure.py
git add pre_commit_hooks/fastapi_cookie_insecure.py tests/test_fastapi_cookie_insecure.py
git commit --no-verify -m "feat: add fastapi-cookie-insecure RGPD hook"
```

---

### Task 15: pii-hardcoded (RGPD)

**Files:**
- Create: `pre_commit_hooks/pii_hardcoded.py`
- Test: `tests/test_pii_hardcoded.py`

**Standard:** PR template "No secrets, credentials, or personal data in the diff" + `claude-config/claude/skills/commit/SKILL.md:63` "Never include customer data … or PII." Detects hardcoded personal-data patterns: French NIR (numéro de sécurité sociale, 15 digits), IBAN, real-looking email (excluding example/test/localhost domains), French phone number. Disable token: `pii-hardcoded: disable`. hooks.yaml excludes tests.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for pii_hardcoded."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.pii_hardcoded import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestPiiHardcoded:
    def test_nir_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'NIR = "183059912345678"\n')]) == 1

    def test_iban_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'IBAN = "FR7630006000011234567890189"\n')]) == 1

    def test_real_email_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'owner = "jean.dupont@gmail.com"\n')]) == 1

    def test_example_email_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'owner = "user@example.com"\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'owner = "jean.dupont@gmail.com"  # pii-hardcoded: disable\n')]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pii_hardcoded.py -v -p no:query_optimizer`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/python3
"""Hook to detect hardcoded personal data (NIR, IBAN, real email, FR phone) in source (RGPD)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_NIR = r'\b[12]\d{2}(?:0[1-9]|1[0-2])\d{10}\b'
_IBAN = r'\bFR\d{2}[0-9A-Z]{23}\b'
_EMAIL = r'\b[A-Za-z0-9._%+-]+@(?!example\.|test\.|localhost)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
_PHONE = r'\b0[1-9](?:[ .]?\d{2}){4}\b'

_PATTERN = re.compile(f'{_NIR}|{_IBAN}|{_EMAIL}|{_PHONE}')
_COMMENTED = re.compile(r'^\s*(#|//)')
_DISABLE = re.compile(r'pii-hardcoded\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect hardcoded personal data and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect hardcoded personal data (RGPD)')


if __name__ == '__main__':
    raise SystemExit(main())
```

Note: the email regex uses a negative lookahead so `example.`/`test.`/`localhost` domains are not flagged. Confirm `user@example.com` passes in Step 4.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pii_hardcoded.py -v -p no:query_optimizer`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
ruff format pre_commit_hooks/pii_hardcoded.py tests/test_pii_hardcoded.py
ruff check pre_commit_hooks/pii_hardcoded.py tests/test_pii_hardcoded.py
git add pre_commit_hooks/pii_hardcoded.py tests/test_pii_hardcoded.py
git commit --no-verify -m "feat: add pii-hardcoded RGPD hook"
```

---

### Task 16: Wire entry points, hook definitions, and docs

**Files:**
- Modify: `pyproject.toml` (`[project.scripts]`)
- Modify: `.pre-commit-hooks.yaml` (append 15 entries)
- Modify: `README.md` (document the new hooks)

**Interfaces:** Consumes every `main` from Tasks 1–15. Produces 15 console scripts and 15 pre-commit hook ids.

- [ ] **Step 1: Add console scripts to `pyproject.toml`**

Under `[project.scripts]`, append (keep the existing entries; add these lines):

```toml
no-external-tool-config = "pre_commit_hooks.no_external_tool_config:main"
no-setup-files = "pre_commit_hooks.no_setup_files:main"
cors-allow-all-detection = "pre_commit_hooks.cors_allow_all:main"
no-create-all = "pre_commit_hooks.no_create_all:main"
os-environ-direct = "pre_commit_hooks.os_environ_direct:main"
file-too-long = "pre_commit_hooks.file_too_long:main"
function-too-long = "pre_commit_hooks.function_too_long:main"
compose-missing-restart = "pre_commit_hooks.compose_missing_restart:main"
react-useeffect-fetch = "pre_commit_hooks.react_useeffect_fetch:main"
sentry-no-default-pii = "pre_commit_hooks.sentry_no_default_pii:main"
react-token-localstorage = "pre_commit_hooks.react_token_localstorage:main"
pii-in-logs = "pre_commit_hooks.pii_in_logs:main"
django-cookie-security = "pre_commit_hooks.django_cookie_security:main"
fastapi-cookie-insecure = "pre_commit_hooks.fastapi_cookie_insecure:main"
pii-hardcoded = "pre_commit_hooks.pii_hardcoded:main"
```

- [ ] **Step 2: Verify all entry points import**

Run: `pip install -e . && python -c "import pre_commit_hooks.no_external_tool_config, pre_commit_hooks.no_setup_files, pre_commit_hooks.cors_allow_all, pre_commit_hooks.no_create_all, pre_commit_hooks.os_environ_direct, pre_commit_hooks.file_too_long, pre_commit_hooks.function_too_long, pre_commit_hooks.compose_missing_restart, pre_commit_hooks.react_useeffect_fetch, pre_commit_hooks.sentry_no_default_pii, pre_commit_hooks.react_token_localstorage, pre_commit_hooks.pii_in_logs, pre_commit_hooks.django_cookie_security, pre_commit_hooks.fastapi_cookie_insecure, pre_commit_hooks.pii_hardcoded; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Append the 15 hook entries to `.pre-commit-hooks.yaml`**

Append (mirror the existing entries' field style; `minimum_pre_commit_version: '4.1.0'` on each):

```yaml
- id: python-no-external-tool-config
  description: detect forbidden standalone tool config files (ruff.toml, mypy.ini, pytest.ini, .coveragerc)
  entry: no-external-tool-config
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect forbidden standalone tool config files
  pass_filenames: true
  files: '(^|/)(ruff\.toml|mypy\.ini|\.mypy\.ini|pytest\.ini|\.coveragerc)$'
- id: python-no-setup-files
  description: detect forbidden setup.py / packaging setup.cfg (use pyproject.toml)
  entry: no-setup-files
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect forbidden setup packaging files
  pass_filenames: true
  files: '(^|/)setup\.(py|cfg)$'
- id: python-cors-allow-all
  description: detect wildcard CORS (allow_origins=['*'] / CORS_ALLOW_ALL_ORIGINS=True)
  entry: cors-allow-all-detection
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect wildcard CORS configuration
  types: ["python"]
- id: python-no-create-all
  description: detect create_all() schema creation outside migrations
  entry: no-create-all
  exclude: 'migrations/|alembic/|tests?/'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect create_all() outside migrations
  types: ["python"]
- id: python-os-environ-direct
  description: detect direct os.environ/os.getenv access outside settings modules
  entry: os-environ-direct
  exclude: 'settings.*\.py|config.*\.py|conftest\.py|tests?/'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect direct os.environ access
  types: ["python"]
- id: python-file-too-long
  description: detect Python files exceeding 500 lines
  entry: file-too-long
  exclude: 'migrations/|tests?/'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect over-long files (>500 lines)
  types: ["python"]
- id: python-function-too-long
  description: detect Python functions exceeding 50 lines
  entry: function-too-long
  exclude: 'tests?/'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect over-long functions (>50 lines)
  types: ["python"]
- id: docker-compose-missing-restart
  additional_dependencies:
    - PyYAML
  description: detect Docker Compose services missing restart: unless-stopped
  entry: compose-missing-restart
  files: '(^|/)docker-compose[^/]*\.ya?ml$'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect compose services missing restart policy
  pass_filenames: true
- id: react-useeffect-fetch
  description: detect data fetching (fetch/axios) inside a React useEffect callback
  entry: react-useeffect-fetch
  files: \.(jsx|tsx)$
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect fetch/axios inside useEffect
  types_or: ["tsx", "jsx", "file"]
- id: sentry-no-default-pii
  description: detect Sentry send_default_pii=True (RGPD)
  entry: sentry-no-default-pii
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect Sentry send_default_pii=True
  types: ["python"]
- id: react-no-token-in-localstorage
  description: detect auth tokens stored in localStorage (RGPD; prefer httpOnly cookies)
  entry: react-token-localstorage
  files: \.(ts|tsx)$
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect auth tokens in localStorage
  types_or: ["ts", "tsx", "file"]
- id: python-pii-in-logs
  description: detect PII (email/token/password/card/ssn/iban/phone) in logging calls (RGPD)
  entry: pii-in-logs
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect PII in logging calls
  types: ["python"]
- id: django-cookie-security
  description: enforce Django production cookie-security flags (RGPD/ePrivacy)
  entry: django-cookie-security
  files: 'settings.*prod.*\.py$|settings/prod\.py$'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: enforce Django cookie-security flags
  pass_filenames: true
  types: ["python"]
- id: fastapi-cookie-insecure
  description: detect set_cookie() missing secure/httponly/samesite (RGPD/ePrivacy)
  entry: fastapi-cookie-insecure
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect insecure set_cookie calls
  pass_filenames: true
  types: ["python"]
- id: pii-hardcoded
  description: detect hardcoded personal data (NIR, IBAN, real email, FR phone) in source (RGPD)
  entry: pii-hardcoded
  exclude: 'tests?/'
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: detect hardcoded personal data
  types_or: ["python", "ts", "tsx", "javascript", "file"]
```

- [ ] **Step 4: Validate the hooks YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.pre-commit-hooks.yaml')); print('ok')"`
Expected: prints `ok`

- [ ] **Step 5: Document the hooks in `README.md`**

Add a `### Standards & RGPD detection hooks` subsection under the "Hooks available" area listing the 15 new hook ids grouped as "Coding standards" (Tasks 1–9) and "RGPD / privacy" (Tasks 10–15), each with its one-line purpose and, where applicable, its `<token>: disable` escape comment.

- [ ] **Step 6: Run the full new-hook test suite**

Run: `python -m pytest tests/test_no_external_tool_config.py tests/test_no_setup_files.py tests/test_cors_allow_all.py tests/test_no_create_all.py tests/test_os_environ_direct.py tests/test_file_too_long.py tests/test_function_too_long.py tests/test_compose_missing_restart.py tests/test_react_useeffect_fetch.py tests/test_sentry_no_default_pii.py tests/test_react_token_localstorage.py tests/test_pii_in_logs.py tests/test_django_cookie_security.py tests/test_fastapi_cookie_insecure.py tests/test_pii_hardcoded.py -v -p no:query_optimizer`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .pre-commit-hooks.yaml README.md
git commit --no-verify -m "feat: wire 15 standards & RGPD detection hooks (entry points + docs)"
```

---

## Self-Review

**Spec coverage:** 9 standards hooks (Tasks 1–9) + 6 RGPD hooks (Tasks 10–15) + wiring (Task 16). Each hook cites the documented standard it enforces. Excludes the user-declined `python-no-python-jose`, the held `python-no-hatchling` (standards contradiction) and `python-library-missing-py-typed` (brittle). ✓

**Placeholder scan:** every code step shows complete code; no TBD/TODO. ✓

**Type/name consistency:** entry-point names in Task 16's `pyproject.toml` and `.pre-commit-hooks.yaml` match the module names created in Tasks 1–15 (e.g. `cors-allow-all-detection` → `cors_allow_all.py`, `react-token-localstorage` → `react_token_localstorage.py`). Disable tokens are consistent between each hook's regex and its tests. ✓

**Detection-core sanity:** regex hooks reuse `PatternDetection` (commented/disable/pattern); structural hooks (filename, line-count, AST, YAML, region-scan, absence-check) carry their full implementation. The region-scan hooks (Tasks 9, 14) handle multi-line calls via balanced-parenthesis scanning, verified by the multi-line test in Task 14.
