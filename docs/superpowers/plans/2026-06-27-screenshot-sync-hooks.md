# Screenshot-sync pre-commit hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two composable pre-commit hooks — `screenshot-capture` and `screenshot-publish` — that screenshot the UI screens affected by a commit and publish them to the README and/or a Notion page.

**Architecture:** `screenshot-capture` reads `.screenshot-sync.yaml`, maps staged files to capture targets via a configurable strategy (`glob-url` / `storybook` / `fixed-routes`), renders them with Playwright, writes PNGs plus a JSON manifest, and `git add`s them. `screenshot-publish` reads that manifest and updates a README section and/or pushes to Notion. The manifest file is the sole interface between the two hooks, so each is testable in isolation (capture needs no network, publish needs no browser).

**Tech Stack:** Python 3.14, Playwright (sync API), PyYAML, `requests` (Notion REST), pytest. Follows the existing `pre_commit_hooks/` patterns.

## Global Constraints

- **Python:** `requires-python = ">=3.14"`. Use `from __future__ import annotations` and PEP 604 unions (`X | None`).
- **Hook file conventions (copy verbatim from existing hooks):** every hook module starts with `#!/usr/bin/python3`, a one-line `"""docstring."""`, then `from __future__ import annotations`. Public entry is `def main(argv: Sequence[str] | None = None) -> int:` and the file ends with `if __name__ == '__main__':\n    raise SystemExit(main())`.
- **User-facing output:** use `print(f'[screenshot-sync] {msg}')  # print-detection: disable`. The trailing `# print-detection: disable` comment is REQUIRED — the repo's own `python-print-detection` hook runs on these files and will fail otherwise.
- **Type annotations:** real annotations, never type comments (the `type annotations not comments` hook enforces this).
- **Never block the commit by default:** on any environment/network problem, print a warning and `return 0`. Only `return 1` when `config.strict is True`.
- **Default config filename:** `.screenshot-sync.yaml`. **Default manifest filename:** `.screenshot-manifest.json` (inside `output_dir`).
- **Known env issue (not caused by this work):** the repo's `pip-audit` pre-commit hook currently fails on pre-existing CVEs in `msgpack 1.2.0` / `pip 26.1.1`. If a commit is blocked solely by `pip-audit`, commit with `git commit --no-verify`. Do NOT use `--no-verify` to bypass any other failing hook.
- **Tests:** `tests/test_<module>.py`, class-grouped, every test method annotated `-> None`. Run with `python -m pytest`.

## File Structure

```
pre_commit_hooks/
  screenshot_capture.py              # Task 8 — main() + orchestration
  screenshot_publish.py              # Task 9 — main() + orchestration
  screenshot_sync/
    __init__.py                      # Task 1 — empty package marker
    reporting.py                     # Task 5 — warn() / skip_or_fail()
    gitutil.py                       # Task 5 — git_add()
    config.py                        # Task 1 — dataclasses + load_config()
    manifest.py                      # Task 2 — Shot + read/write_manifest()
    capture/
      __init__.py                    # Task 3 — resolve_targets() dispatcher
      targets.py                     # Task 3 — CaptureTarget + matches()
      glob_url.py                    # Task 3
      fixed_routes.py                # Task 3
      storybook.py                   # Task 3
      runner.py                      # Task 4 — Playwright wrapper
    publish/
      __init__.py                    # Task 6 — empty package marker
      readme.py                      # Task 6 — render_section/inject/update_readme_file
      notion.py                      # Task 7 — build_blocks/publish
tests/
  test_screenshot_config.py          # Task 1
  test_screenshot_manifest.py        # Task 2
  test_screenshot_capture_targets.py # Task 3
  test_screenshot_runner.py          # Task 4
  test_screenshot_gitutil.py         # Task 5
  test_screenshot_readme.py          # Task 6
  test_screenshot_notion.py          # Task 7
  test_screenshot_capture_hook.py    # Task 8
  test_screenshot_publish_hook.py    # Task 9
pyproject.toml                       # Task 10 — [project.scripts]
.pre-commit-hooks.yaml               # Task 10 — two hook entries
README.md                            # Task 10 — docs section
```

---

### Task 1: Config loader

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/__init__.py`
- Create: `pre_commit_hooks/screenshot_sync/config.py`
- Test: `tests/test_screenshot_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `CONFIG_FILENAME = '.screenshot-sync.yaml'`
  - dataclasses `Viewport(width:int=1280, height:int=800)`, `Route(match:str, url:str, name:str)`, `FixedRoute(url:str, name:str)`, `StoryEntry(match:str, id:str, name:str)`, `ReadmePublish(enabled:bool=True, file:str='README.md', marker:str='screenshots')`, `NotionPublish(enabled:bool=False, page_id:str='', image_base_url:str='')`, `PublishConfig(readme:ReadmePublish, notion:NotionPublish)`, `Config(strategy:str, base_url:str, output_dir:str, viewport:Viewport, strict:bool, routes:list[Route], fixed_routes:list[FixedRoute], storybook_url:str, stories:list[StoryEntry], publish:PublishConfig)`
  - `class ConfigError(ValueError)`
  - `def load_config(path: str | Path = CONFIG_FILENAME) -> Config | None` — returns `None` if file absent, raises `ConfigError` on malformed/invalid.

- [ ] **Step 1: Create the package marker**

Create `pre_commit_hooks/screenshot_sync/__init__.py` containing exactly:

```python
"""Screenshot-sync hook internals (capture + publish)."""
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_screenshot_config.py`:

```python
"""Tests for screenshot_sync.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.screenshot_sync.config import ConfigError, load_config


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / '.screenshot-sync.yaml'
    path.write_text(body, encoding='utf-8')
    return path


class TestLoadConfig:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert load_config(tmp_path / 'nope.yaml') is None

    def test_glob_url_minimal(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            'strategy: glob-url\n'
            'base_url: http://localhost:5173\n'
            'routes:\n'
            '  - {match: "src/pages/Login.*", url: /login, name: login}\n',
        )
        config = load_config(path)
        assert config is not None
        assert config.strategy == 'glob-url'
        assert config.base_url == 'http://localhost:5173'
        assert config.output_dir == 'docs/screenshots'
        assert config.strict is False
        assert config.viewport.width == 1280
        assert config.routes[0].url == '/login'
        assert config.routes[0].name == 'login'
        assert config.publish.readme.enabled is True
        assert config.publish.readme.marker == 'screenshots'
        assert config.publish.notion.enabled is False

    def test_fixed_routes_and_overrides(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            'strategy: fixed-routes\n'
            'base_url: http://localhost:3000\n'
            'output_dir: shots\n'
            'strict: true\n'
            'viewport: {width: 800, height: 600}\n'
            'fixed_routes:\n'
            '  - {url: /, name: home}\n'
            'publish:\n'
            '  readme: {enabled: false, file: docs/UI.md, marker: shots}\n'
            '  notion: {enabled: true, page_id: abc123, image_base_url: https://cdn/x}\n',
        )
        config = load_config(path)
        assert config is not None
        assert config.output_dir == 'shots'
        assert config.strict is True
        assert config.viewport.height == 600
        assert config.fixed_routes[0].name == 'home'
        assert config.publish.readme.enabled is False
        assert config.publish.readme.file == 'docs/UI.md'
        assert config.publish.notion.enabled is True
        assert config.publish.notion.page_id == 'abc123'
        assert config.publish.notion.image_base_url == 'https://cdn/x'

    def test_storybook_strategy(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            'strategy: storybook\n'
            'storybook:\n'
            '  url: http://localhost:6006\n'
            '  stories:\n'
            '    - {match: "src/Button.*", id: button--primary, name: button}\n',
        )
        config = load_config(path)
        assert config is not None
        assert config.storybook_url == 'http://localhost:6006'
        assert config.stories[0].id == 'button--primary'

    def test_unknown_strategy_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'strategy: magic\n')
        with pytest.raises(ConfigError):
            load_config(path)

    def test_missing_strategy_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'base_url: http://x\n')
        with pytest.raises(ConfigError):
            load_config(path)

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'strategy: [unclosed\n')
        with pytest.raises(ConfigError):
            load_config(path)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.config'`

- [ ] **Step 4: Write the implementation**

Create `pre_commit_hooks/screenshot_sync/config.py`:

```python
#!/usr/bin/python3
"""Load and validate the .screenshot-sync.yaml config file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_FILENAME = '.screenshot-sync.yaml'
_STRATEGIES = {'glob-url', 'storybook', 'fixed-routes'}


class ConfigError(ValueError):
    """Raised when the config file exists but is malformed or invalid."""


@dataclass
class Viewport:
    width: int = 1280
    height: int = 800


@dataclass
class Route:
    match: str
    url: str
    name: str


@dataclass
class FixedRoute:
    url: str
    name: str


@dataclass
class StoryEntry:
    match: str
    id: str
    name: str


@dataclass
class ReadmePublish:
    enabled: bool = True
    file: str = 'README.md'
    marker: str = 'screenshots'


@dataclass
class NotionPublish:
    enabled: bool = False
    page_id: str = ''
    image_base_url: str = ''


@dataclass
class PublishConfig:
    readme: ReadmePublish = field(default_factory=ReadmePublish)
    notion: NotionPublish = field(default_factory=NotionPublish)


@dataclass
class Config:
    strategy: str
    base_url: str
    output_dir: str
    viewport: Viewport
    strict: bool
    routes: list[Route]
    fixed_routes: list[FixedRoute]
    storybook_url: str
    stories: list[StoryEntry]
    publish: PublishConfig


def _as_dict(value: object, label: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f'{label} must be a mapping, got {type(value).__name__}')
    return value


def load_config(path: str | Path = CONFIG_FILENAME) -> Config | None:
    """Return the parsed Config, or None when the file does not exist."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f'invalid YAML in {path}: {exc}') from exc
    if not isinstance(raw, dict):
        raise ConfigError(f'{path} must contain a mapping at the top level')

    strategy = raw.get('strategy')
    if strategy not in _STRATEGIES:
        raise ConfigError(
            f'strategy must be one of {sorted(_STRATEGIES)}, got {strategy!r}'
        )

    viewport_raw = _as_dict(raw.get('viewport'), 'viewport')
    viewport = Viewport(
        width=int(viewport_raw.get('width', 1280)),
        height=int(viewport_raw.get('height', 800)),
    )

    routes = [
        Route(match=r['match'], url=r['url'], name=r['name'])
        for r in raw.get('routes', []) or []
    ]
    fixed_routes = [
        FixedRoute(url=r['url'], name=r['name'])
        for r in raw.get('fixed_routes', []) or []
    ]
    storybook_raw = _as_dict(raw.get('storybook'), 'storybook')
    stories = [
        StoryEntry(match=s['match'], id=s['id'], name=s['name'])
        for s in storybook_raw.get('stories', []) or []
    ]

    publish_raw = _as_dict(raw.get('publish'), 'publish')
    readme_raw = _as_dict(publish_raw.get('readme'), 'publish.readme')
    notion_raw = _as_dict(publish_raw.get('notion'), 'publish.notion')
    publish = PublishConfig(
        readme=ReadmePublish(
            enabled=bool(readme_raw.get('enabled', True)),
            file=str(readme_raw.get('file', 'README.md')),
            marker=str(readme_raw.get('marker', 'screenshots')),
        ),
        notion=NotionPublish(
            enabled=bool(notion_raw.get('enabled', False)),
            page_id=str(notion_raw.get('page_id', '')),
            image_base_url=str(notion_raw.get('image_base_url', '')),
        ),
    )

    try:
        return Config(
            strategy=strategy,
            base_url=str(raw.get('base_url', '')),
            output_dir=str(raw.get('output_dir', 'docs/screenshots')),
            viewport=viewport,
            strict=bool(raw.get('strict', False)),
            routes=routes,
            fixed_routes=fixed_routes,
            storybook_url=str(storybook_raw.get('url', '')),
            stories=stories,
            publish=publish,
        )
    except (KeyError, TypeError) as exc:
        raise ConfigError(f'invalid config in {path}: {exc}') from exc
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_config.py -v`
Expected: PASS (7 passed)

- [ ] **Step 6: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/__init__.py pre_commit_hooks/screenshot_sync/config.py tests/test_screenshot_config.py
git commit -m "feat: add screenshot-sync config loader"
```

---

### Task 2: Manifest read/write

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/manifest.py`
- Test: `tests/test_screenshot_manifest.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `MANIFEST_FILENAME = '.screenshot-manifest.json'`
  - `@dataclass class Shot(name:str, path:str, url:str)`
  - `def manifest_path(output_dir: str | Path) -> Path`
  - `def write_manifest(output_dir: str | Path, shots: list[Shot]) -> Path` — creates `output_dir`, writes JSON, returns the manifest path.
  - `def read_manifest(output_dir: str | Path) -> list[Shot]` — returns `[]` when the manifest is absent.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_manifest.py`:

```python
"""Tests for screenshot_sync.manifest."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.screenshot_sync.manifest import (
    Shot,
    manifest_path,
    read_manifest,
    write_manifest,
)


class TestManifest:
    def test_read_missing_returns_empty(self, tmp_path: Path) -> None:
        assert read_manifest(tmp_path / 'shots') == []

    def test_write_then_read_roundtrip(self, tmp_path: Path) -> None:
        out = tmp_path / 'shots'
        shots = [
            Shot(name='login', path='shots/login.png', url='/login'),
            Shot(name='home', path='shots/home.png', url='/'),
        ]
        returned = write_manifest(out, shots)
        assert returned == manifest_path(out)
        assert returned.exists()
        assert read_manifest(out) == shots

    def test_write_creates_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / 'nested' / 'shots'
        write_manifest(out, [Shot(name='a', path='a.png', url='/a')])
        assert out.is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_manifest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.manifest'`

- [ ] **Step 3: Write the implementation**

Create `pre_commit_hooks/screenshot_sync/manifest.py`:

```python
#!/usr/bin/python3
"""Read and write the screenshot manifest shared by capture and publish."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

MANIFEST_FILENAME = '.screenshot-manifest.json'


@dataclass
class Shot:
    name: str
    path: str
    url: str


def manifest_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / MANIFEST_FILENAME


def write_manifest(output_dir: str | Path, shots: list[Shot]) -> Path:
    """Write the manifest under output_dir, creating the directory if needed."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = manifest_path(out)
    payload = {'shots': [asdict(shot) for shot in shots]}
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return path


def read_manifest(output_dir: str | Path) -> list[Shot]:
    """Return the manifest's shots, or an empty list when it does not exist."""
    path = manifest_path(output_dir)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return [Shot(**entry) for entry in data.get('shots', [])]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_manifest.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/manifest.py tests/test_screenshot_manifest.py
git commit -m "feat: add screenshot-sync manifest read/write"
```

---

### Task 3: Capture target resolution (3 strategies + dispatcher)

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/capture/__init__.py`
- Create: `pre_commit_hooks/screenshot_sync/capture/targets.py`
- Create: `pre_commit_hooks/screenshot_sync/capture/glob_url.py`
- Create: `pre_commit_hooks/screenshot_sync/capture/fixed_routes.py`
- Create: `pre_commit_hooks/screenshot_sync/capture/storybook.py`
- Test: `tests/test_screenshot_capture_targets.py`

**Interfaces:**
- Consumes: `Config` (Task 1).
- Produces:
  - In `targets.py`: `@dataclass class CaptureTarget(name:str, url:str, full_url:str)` and `def matches(filepath: str, pattern: str) -> bool`.
  - In each strategy module: `def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]`.
  - In `capture/__init__.py`: `def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]` — dispatches on `config.strategy`. Results are de-duplicated by `name`, preserving first-seen order.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_capture_targets.py`:

```python
"""Tests for screenshot_sync.capture target resolution."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture import resolve_targets
from pre_commit_hooks.screenshot_sync.capture.targets import matches
from pre_commit_hooks.screenshot_sync.config import (
    Config,
    FixedRoute,
    PublishConfig,
    Route,
    StoryEntry,
    Viewport,
)


def _config(**overrides: object) -> Config:
    base: dict[str, object] = {
        'strategy': 'glob-url',
        'base_url': 'http://localhost:5173',
        'output_dir': 'docs/screenshots',
        'viewport': Viewport(),
        'strict': False,
        'routes': [],
        'fixed_routes': [],
        'storybook_url': 'http://localhost:6006',
        'stories': [],
        'publish': PublishConfig(),
    }
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]  # test helper builds a full kwargs dict


class TestMatches:
    def test_full_path_glob(self) -> None:
        assert matches('src/pages/Login.tsx', 'src/pages/Login.*') is True

    def test_basename_glob(self) -> None:
        assert matches('deep/nested/Login.tsx', 'Login.*') is True

    def test_no_match(self) -> None:
        assert matches('src/util.ts', 'src/pages/Login.*') is False


class TestGlobUrl:
    def test_changed_file_maps_to_route(self) -> None:
        config = _config(
            routes=[Route(match='src/pages/Login.*', url='/login', name='login')],
        )
        targets = resolve_targets(config, ['src/pages/Login.tsx'])
        assert len(targets) == 1
        assert targets[0].name == 'login'
        assert targets[0].url == '/login'
        assert targets[0].full_url == 'http://localhost:5173/login'

    def test_unmatched_file_yields_nothing(self) -> None:
        config = _config(
            routes=[Route(match='src/pages/Login.*', url='/login', name='login')],
        )
        assert resolve_targets(config, ['src/util.ts']) == []

    def test_dedup_by_name(self) -> None:
        config = _config(
            routes=[Route(match='src/pages/Login.*', url='/login', name='login')],
        )
        targets = resolve_targets(config, ['src/pages/Login.tsx', 'src/pages/Login.css'])
        assert len(targets) == 1


class TestFixedRoutes:
    def test_any_change_captures_all(self) -> None:
        config = _config(
            strategy='fixed-routes',
            base_url='http://localhost:3000',
            fixed_routes=[FixedRoute(url='/', name='home'), FixedRoute(url='/about', name='about')],
        )
        targets = resolve_targets(config, ['src/anything.tsx'])
        assert [t.name for t in targets] == ['home', 'about']
        assert targets[0].full_url == 'http://localhost:3000/'

    def test_no_changes_yields_nothing(self) -> None:
        config = _config(
            strategy='fixed-routes',
            fixed_routes=[FixedRoute(url='/', name='home')],
        )
        assert resolve_targets(config, []) == []


class TestStorybook:
    def test_changed_component_maps_to_story(self) -> None:
        config = _config(
            strategy='storybook',
            stories=[StoryEntry(match='src/Button.*', id='comp-button--primary', name='button')],
        )
        targets = resolve_targets(config, ['src/Button.tsx'])
        assert len(targets) == 1
        assert targets[0].name == 'button'
        assert targets[0].url == 'iframe.html?id=comp-button--primary'
        assert targets[0].full_url == 'http://localhost:6006/iframe.html?id=comp-button--primary'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_capture_targets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.capture'`

- [ ] **Step 3: Write `targets.py`**

Create `pre_commit_hooks/screenshot_sync/capture/targets.py`:

```python
#!/usr/bin/python3
"""Shared capture-target type and glob matching helper."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CaptureTarget:
    name: str
    url: str
    full_url: str


def matches(filepath: str, pattern: str) -> bool:
    """Return True if filepath matches pattern on the full path or basename."""
    name = Path(filepath).name
    return fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(name, pattern)
```

- [ ] **Step 4: Write the three strategy modules**

Create `pre_commit_hooks/screenshot_sync/capture/glob_url.py`:

```python
#!/usr/bin/python3
"""glob-url strategy: map changed files to base_url + route."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget, matches
from pre_commit_hooks.screenshot_sync.config import Config


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    base = config.base_url.rstrip('/')
    targets: list[CaptureTarget] = []
    for route in config.routes:
        if any(matches(path, route.match) for path in changed_files):
            targets.append(
                CaptureTarget(
                    name=route.name,
                    url=route.url,
                    full_url=f'{base}{route.url}',
                )
            )
    return targets
```

Create `pre_commit_hooks/screenshot_sync/capture/fixed_routes.py`:

```python
#!/usr/bin/python3
"""fixed-routes strategy: capture every configured route when any file changed."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Config


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    if not changed_files:
        return []
    base = config.base_url.rstrip('/')
    return [
        CaptureTarget(name=route.name, url=route.url, full_url=f'{base}{route.url}')
        for route in config.fixed_routes
    ]
```

Create `pre_commit_hooks/screenshot_sync/capture/storybook.py`:

```python
#!/usr/bin/python3
"""storybook strategy: map changed components to Storybook iframe URLs."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget, matches
from pre_commit_hooks.screenshot_sync.config import Config


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    base = config.storybook_url.rstrip('/')
    targets: list[CaptureTarget] = []
    for story in config.stories:
        if any(matches(path, story.match) for path in changed_files):
            ref = f'iframe.html?id={story.id}'
            targets.append(
                CaptureTarget(name=story.name, url=ref, full_url=f'{base}/{ref}')
            )
    return targets
```

- [ ] **Step 5: Write the dispatcher**

Create `pre_commit_hooks/screenshot_sync/capture/__init__.py`:

```python
"""Capture target resolution: dispatch on the configured strategy."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture import (
    fixed_routes,
    glob_url,
    storybook,
)
from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Config

_STRATEGIES = {
    'glob-url': glob_url.resolve_targets,
    'fixed-routes': fixed_routes.resolve_targets,
    'storybook': storybook.resolve_targets,
}


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    """Resolve capture targets for the configured strategy, de-duped by name."""
    resolver = _STRATEGIES[config.strategy]
    seen: set[str] = set()
    unique: list[CaptureTarget] = []
    for target in resolver(config, changed_files):
        if target.name not in seen:
            seen.add(target.name)
            unique.append(target)
    return unique
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_capture_targets.py -v`
Expected: PASS (10 passed)

- [ ] **Step 7: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/capture tests/test_screenshot_capture_targets.py
git commit -m "feat: add screenshot-sync capture target resolution"
```

---

### Task 4: Playwright runner

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/capture/runner.py`
- Test: `tests/test_screenshot_runner.py`

**Interfaces:**
- Consumes: `CaptureTarget` (Task 3), `Viewport` (Task 1), `Shot` (Task 2).
- Produces:
  - `class BrowserUnavailableError(RuntimeError)`
  - `class CaptureFailedError(RuntimeError)`
  - `def capture_targets(targets: list[CaptureTarget], output_dir: str | Path, viewport: Viewport) -> list[Shot]` — renders each target to `output_dir/<name>.png`, returns `Shot(name, path=str(output_dir/<name>.png), url=target.url)` for each. Raises `BrowserUnavailableError` if Playwright or its browser binary is missing; `CaptureFailedError` if a page fails to load.

**Implementation note:** the module imports Playwright lazily inside `capture_targets` and references `sync_playwright` through the module global so tests can monkeypatch `pre_commit_hooks.screenshot_sync.capture.runner.sync_playwright` with a fake. The real browser is never launched in tests.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_runner.py`:

```python
"""Tests for screenshot_sync.capture.runner (Playwright mocked)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.screenshot_sync.capture import runner
from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Viewport


class _FakePage:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self._rec = recorder

    def set_viewport_size(self, size: dict[str, int]) -> None:
        self._rec.append(('viewport', size))

    def goto(self, url: str, wait_until: str = 'load', timeout: float = 0) -> None:
        self._rec.append(('goto', url))

    def screenshot(self, path: str, full_page: bool = True) -> None:
        self._rec.append(('screenshot', path))
        Path(path).write_bytes(b'PNG')


class _FakeBrowser:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self._rec = recorder

    def new_page(self) -> _FakePage:
        return _FakePage(self._rec)

    def close(self) -> None:
        self._rec.append(('close', None))


class _FakeChromium:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self._rec = recorder

    def launch(self) -> _FakeBrowser:
        return _FakeBrowser(self._rec)


class _FakePlaywrightCtx:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self.chromium = _FakeChromium(recorder)

    def __enter__(self) -> _FakePlaywrightCtx:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _fake_sync_playwright(recorder: list[tuple[str, object]]):
    def factory() -> _FakePlaywrightCtx:
        return _FakePlaywrightCtx(recorder)

    return factory


class TestCaptureTargets:
    def test_writes_png_and_returns_shots(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorder: list[tuple[str, object]] = []
        monkeypatch.setattr(runner, 'sync_playwright', _fake_sync_playwright(recorder))
        out = tmp_path / 'shots'
        targets = [CaptureTarget(name='home', url='/', full_url='http://x/')]
        shots = runner.capture_targets(targets, out, Viewport(width=800, height=600))
        assert len(shots) == 1
        assert shots[0].name == 'home'
        assert shots[0].url == '/'
        assert Path(shots[0].path).exists()
        assert ('goto', 'http://x/') in recorder
        assert ('viewport', {'width': 800, 'height': 600}) in recorder

    def test_missing_playwright_raises_browser_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(runner, 'sync_playwright', None)
        with pytest.raises(runner.BrowserUnavailableError):
            runner.capture_targets(
                [CaptureTarget(name='a', url='/a', full_url='http://x/a')],
                'shots',
                Viewport(),
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.capture.runner'`

- [ ] **Step 3: Write the implementation**

Create `pre_commit_hooks/screenshot_sync/capture/runner.py`:

```python
#!/usr/bin/python3
"""Render capture targets to PNG files with Playwright."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Viewport
from pre_commit_hooks.screenshot_sync.manifest import Shot

try:  # Playwright is an optional, heavy dependency.
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised via monkeypatch in tests
    sync_playwright = None


class BrowserUnavailableError(RuntimeError):
    """Raised when Playwright or its browser binary is not installed."""


class CaptureFailedError(RuntimeError):
    """Raised when a page cannot be loaded or screenshotted."""


def capture_targets(
    targets: list[CaptureTarget],
    output_dir: str | Path,
    viewport: Viewport,
) -> list[Shot]:
    """Screenshot every target; return one Shot per captured target."""
    if sync_playwright is None:
        raise BrowserUnavailableError('playwright is not installed')

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    shots: list[Shot] = []
    try:
        with sync_playwright() as play:
            browser = play.chromium.launch()
            try:
                page = browser.new_page()
                page.set_viewport_size({'width': viewport.width, 'height': viewport.height})
                for target in targets:
                    png = out / f'{target.name}.png'
                    try:
                        page.goto(target.full_url, wait_until='networkidle', timeout=15000)
                        page.screenshot(path=str(png), full_page=True)
                    except Exception as exc:  # noqa: BLE001 - re-raised as domain error
                        raise CaptureFailedError(
                            f'failed to capture {target.full_url}: {exc}'
                        ) from exc
                    shots.append(Shot(name=target.name, path=str(png), url=target.url))
            finally:
                browser.close()
    except CaptureFailedError:
        raise
    except Exception as exc:  # noqa: BLE001 - launch/driver problems => unavailable
        raise BrowserUnavailableError(f'cannot launch browser: {exc}') from exc
    return shots
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_runner.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/capture/runner.py tests/test_screenshot_runner.py
git commit -m "feat: add screenshot-sync Playwright runner"
```

---

### Task 5: git + reporting helpers

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/gitutil.py`
- Create: `pre_commit_hooks/screenshot_sync/reporting.py`
- Test: `tests/test_screenshot_gitutil.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - In `gitutil.py`: `def git_add(paths: list[str]) -> None` — runs `git add -- <paths>` via `subprocess.run(..., check=False)`; no-op when `paths` is empty.
  - In `reporting.py`: `def warn(message: str) -> None` (prints `[screenshot-sync] <message>`) and `def skip_or_fail(strict: bool, message: str) -> int` (warns, returns `1` if `strict` else `0`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_gitutil.py`:

```python
"""Tests for screenshot_sync.gitutil and reporting."""

from __future__ import annotations

import pytest

from pre_commit_hooks.screenshot_sync import gitutil, reporting


class TestGitAdd:
    def test_calls_git_add_with_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[list[str]] = []
        monkeypatch.setattr(
            gitutil.subprocess, 'run', lambda cmd, **kw: calls.append(cmd)
        )
        gitutil.git_add(['docs/screenshots', 'README.md'])
        assert calls == [['git', 'add', '--', 'docs/screenshots', 'README.md']]

    def test_empty_paths_is_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[list[str]] = []
        monkeypatch.setattr(
            gitutil.subprocess, 'run', lambda cmd, **kw: calls.append(cmd)
        )
        gitutil.git_add([])
        assert calls == []


class TestReporting:
    def test_skip_returns_zero_when_not_strict(self, capsys: pytest.CaptureFixture) -> None:
        assert reporting.skip_or_fail(False, 'boom') == 0
        assert '[screenshot-sync] boom' in capsys.readouterr().out

    def test_fail_returns_one_when_strict(self, capsys: pytest.CaptureFixture) -> None:
        assert reporting.skip_or_fail(True, 'boom') == 1
        assert '[screenshot-sync] boom' in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_gitutil.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.gitutil'`

- [ ] **Step 3: Write the implementations**

Create `pre_commit_hooks/screenshot_sync/gitutil.py`:

```python
#!/usr/bin/python3
"""Stage generated files into the git index."""

from __future__ import annotations

import subprocess


def git_add(paths: list[str]) -> None:
    """Stage the given paths; no-op when the list is empty."""
    if not paths:
        return
    subprocess.run(['git', 'add', '--', *paths], check=False)
```

Create `pre_commit_hooks/screenshot_sync/reporting.py`:

```python
#!/usr/bin/python3
"""User-facing warnings and the skip/fail decision for the hooks."""

from __future__ import annotations


def warn(message: str) -> None:
    print(f'[screenshot-sync] {message}')  # print-detection: disable


def skip_or_fail(strict: bool, message: str) -> int:
    """Warn, then return 1 when strict (block the commit) else 0 (skip)."""
    warn(message)
    return 1 if strict else 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_gitutil.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/gitutil.py pre_commit_hooks/screenshot_sync/reporting.py tests/test_screenshot_gitutil.py
git commit -m "feat: add screenshot-sync git and reporting helpers"
```

---

### Task 6: README publisher

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/publish/__init__.py`
- Create: `pre_commit_hooks/screenshot_sync/publish/readme.py`
- Test: `tests/test_screenshot_readme.py`

**Interfaces:**
- Consumes: `Shot` (Task 2).
- Produces:
  - `def render_section(shots: list[Shot]) -> str` — markdown body, one `![name](path)` per shot, newline-separated.
  - `def inject(text: str, section: str, marker: str) -> str` — replaces content between `<!-- {marker}:start -->` and `<!-- {marker}:end -->`; appends a fresh marker block at end of file if markers absent; idempotent.
  - `def update_readme_file(file: str | Path, shots: list[Shot], marker: str) -> bool` — reads file (empty string if missing), injects, writes back; returns `True` if the file content changed.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_readme.py`:

```python
"""Tests for screenshot_sync.publish.readme."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.screenshot_sync.manifest import Shot
from pre_commit_hooks.screenshot_sync.publish import readme

_SHOTS = [
    Shot(name='login', path='docs/screenshots/login.png', url='/login'),
    Shot(name='home', path='docs/screenshots/home.png', url='/'),
]


class TestRenderSection:
    def test_one_image_line_per_shot(self) -> None:
        section = readme.render_section(_SHOTS)
        assert '![login](docs/screenshots/login.png)' in section
        assert '![home](docs/screenshots/home.png)' in section


class TestInject:
    def test_replaces_between_existing_markers(self) -> None:
        text = (
            '# Title\n\n'
            '<!-- shots:start -->\n'
            'OLD\n'
            '<!-- shots:end -->\n'
        )
        result = readme.inject(text, 'NEW', 'shots')
        assert 'OLD' not in result
        assert 'NEW' in result
        assert result.count('<!-- shots:start -->') == 1

    def test_appends_markers_when_absent(self) -> None:
        result = readme.inject('# Title\n', 'BODY', 'shots')
        assert '<!-- shots:start -->' in result
        assert '<!-- shots:end -->' in result
        assert 'BODY' in result

    def test_idempotent(self) -> None:
        once = readme.inject('# Title\n', 'BODY', 'shots')
        twice = readme.inject(once, 'BODY', 'shots')
        assert once == twice


class TestUpdateReadmeFile:
    def test_creates_section_and_reports_change(self, tmp_path: Path) -> None:
        path = tmp_path / 'README.md'
        path.write_text('# Project\n', encoding='utf-8')
        changed = readme.update_readme_file(path, _SHOTS, 'screenshots')
        assert changed is True
        body = path.read_text(encoding='utf-8')
        assert '<!-- screenshots:start -->' in body
        assert '![login](docs/screenshots/login.png)' in body

    def test_no_change_returns_false(self, tmp_path: Path) -> None:
        path = tmp_path / 'README.md'
        path.write_text('# Project\n', encoding='utf-8')
        readme.update_readme_file(path, _SHOTS, 'screenshots')
        changed_again = readme.update_readme_file(path, _SHOTS, 'screenshots')
        assert changed_again is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_readme.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.publish'`

- [ ] **Step 3: Write the package marker and implementation**

Create `pre_commit_hooks/screenshot_sync/publish/__init__.py` containing exactly:

```python
"""Screenshot-sync publishers (README, Notion)."""
```

Create `pre_commit_hooks/screenshot_sync/publish/readme.py`:

```python
#!/usr/bin/python3
"""Inject a screenshots section into a README between HTML markers."""

from __future__ import annotations

import re
from pathlib import Path

from pre_commit_hooks.screenshot_sync.manifest import Shot


def render_section(shots: list[Shot]) -> str:
    """Return the markdown body: one image per shot."""
    return '\n'.join(f'![{shot.name}]({shot.path})' for shot in shots)


def inject(text: str, section: str, marker: str) -> str:
    """Replace content between the marker comments, creating them if absent."""
    start = f'<!-- {marker}:start -->'
    end = f'<!-- {marker}:end -->'
    block = f'{start}\n{section}\n{end}'
    pattern = re.compile(
        re.escape(start) + r'.*?' + re.escape(end),
        re.DOTALL,
    )
    if pattern.search(text):
        return pattern.sub(block, text)
    separator = '' if text.endswith('\n') or text == '' else '\n'
    return f'{text}{separator}\n{block}\n'


def update_readme_file(file: str | Path, shots: list[Shot], marker: str) -> bool:
    """Inject the rendered section into file; return True if content changed."""
    path = Path(file)
    original = path.read_text(encoding='utf-8') if path.exists() else ''
    updated = inject(original, render_section(shots), marker)
    if updated == original:
        return False
    path.write_text(updated, encoding='utf-8')
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_readme.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/publish/__init__.py pre_commit_hooks/screenshot_sync/publish/readme.py tests/test_screenshot_readme.py
git commit -m "feat: add screenshot-sync README publisher"
```

---

### Task 7: Notion publisher

**Files:**
- Create: `pre_commit_hooks/screenshot_sync/publish/notion.py`
- Test: `tests/test_screenshot_notion.py`

**Interfaces:**
- Consumes: `Shot` (Task 2).
- Produces:
  - `class NotionError(RuntimeError)`
  - `def build_blocks(shots: list[Shot], image_base_url: str) -> list[dict]` — when `image_base_url` is non-empty, an external `image` block per shot (`url = image_base_url.rstrip('/') + '/' + shot.path`); otherwise a `paragraph` block per shot with the shot name and path as text (honest fallback: Notion cannot host local files).
  - `def publish(page_id: str, shots: list[Shot], token: str, image_base_url: str) -> None` — `PATCH https://api.notion.com/v1/blocks/{page_id}/children` with the blocks; raises `NotionError` on a non-2xx response or a network error. References `requests` through the module global for monkeypatching.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_notion.py`:

```python
"""Tests for screenshot_sync.publish.notion (requests mocked)."""

from __future__ import annotations

import pytest

from pre_commit_hooks.screenshot_sync.manifest import Shot
from pre_commit_hooks.screenshot_sync.publish import notion

_SHOTS = [Shot(name='login', path='docs/screenshots/login.png', url='/login')]


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.text = 'error-body'


class TestBuildBlocks:
    def test_external_image_when_base_url(self) -> None:
        blocks = notion.build_blocks(_SHOTS, 'https://cdn.example/repo')
        assert blocks[0]['type'] == 'image'
        assert (
            blocks[0]['image']['external']['url']
            == 'https://cdn.example/repo/docs/screenshots/login.png'
        )

    def test_paragraph_fallback_without_base_url(self) -> None:
        blocks = notion.build_blocks(_SHOTS, '')
        assert blocks[0]['type'] == 'paragraph'
        text = blocks[0]['paragraph']['rich_text'][0]['text']['content']
        assert 'login' in text


class TestPublish:
    def test_posts_to_children_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_patch(url: str, *, headers: dict, json: dict, timeout: float) -> _FakeResponse:
            captured['url'] = url
            captured['headers'] = headers
            captured['json'] = json
            return _FakeResponse(200)

        monkeypatch.setattr(notion.requests, 'patch', fake_patch)
        notion.publish('page123', _SHOTS, 'secret-token', 'https://cdn/x')
        assert captured['url'] == 'https://api.notion.com/v1/blocks/page123/children'
        assert captured['headers']['Authorization'] == 'Bearer secret-token'
        assert 'Notion-Version' in captured['headers']
        assert captured['json']['children'][0]['type'] == 'image'

    def test_non_2xx_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            notion.requests, 'patch', lambda *a, **k: _FakeResponse(401)
        )
        with pytest.raises(notion.NotionError):
            notion.publish('page123', _SHOTS, 'bad', '')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_notion.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_sync.publish.notion'`

- [ ] **Step 3: Write the implementation**

Create `pre_commit_hooks/screenshot_sync/publish/notion.py`:

```python
#!/usr/bin/python3
"""Append screenshot blocks to a Notion page via the REST API."""

from __future__ import annotations

import requests

from pre_commit_hooks.screenshot_sync.manifest import Shot

_API_VERSION = '2022-06-28'


class NotionError(RuntimeError):
    """Raised when the Notion API call fails."""


def build_blocks(shots: list[Shot], image_base_url: str) -> list[dict]:
    """Build Notion block payloads for the shots."""
    base = image_base_url.rstrip('/')
    blocks: list[dict] = []
    for shot in shots:
        if base:
            blocks.append(
                {
                    'object': 'block',
                    'type': 'image',
                    'image': {
                        'type': 'external',
                        'external': {'url': f'{base}/{shot.path}'},
                    },
                }
            )
        else:
            blocks.append(
                {
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': f'{shot.name}: {shot.path}'},
                            }
                        ]
                    },
                }
            )
    return blocks


def publish(page_id: str, shots: list[Shot], token: str, image_base_url: str) -> None:
    """Append the shots as blocks to the given Notion page."""
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': _API_VERSION,
        'Content-Type': 'application/json',
    }
    payload = {'children': build_blocks(shots, image_base_url)}
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise NotionError(f'Notion request failed: {exc}') from exc
    if not 200 <= response.status_code < 300:
        raise NotionError(
            f'Notion API returned {response.status_code}: {response.text}'
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_notion.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_sync/publish/notion.py tests/test_screenshot_notion.py
git commit -m "feat: add screenshot-sync Notion publisher"
```

---

### Task 8: `screenshot-capture` hook

**Files:**
- Create: `pre_commit_hooks/screenshot_capture.py`
- Test: `tests/test_screenshot_capture_hook.py`

**Interfaces:**
- Consumes: `load_config` (Task 1), `resolve_targets` (Task 3), `capture_targets`/`BrowserUnavailableError`/`CaptureFailedError` (Task 4), `write_manifest` (Task 2), `git_add` (Task 5), `skip_or_fail` (Task 5).
- Produces: `def main(argv: Sequence[str] | None = None) -> int`. Filenames come from argv (pre-commit `pass_filenames: true`).

**Orchestration:** no config → `return 0`. No targets → `return 0`. On `BrowserUnavailableError`/`CaptureFailedError` → `return skip_or_fail(config.strict, msg)`. On success → write manifest, `git_add([output_dir])`, `return 0`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_capture_hook.py`:

```python
"""Tests for the screenshot-capture hook orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks import screenshot_capture
from pre_commit_hooks.screenshot_sync.capture import runner
from pre_commit_hooks.screenshot_sync.manifest import Shot, read_manifest


def _write_config(tmp_path: Path, body: str) -> None:
    (tmp_path / '.screenshot-sync.yaml').write_text(body, encoding='utf-8')


_GLOB_CONFIG = (
    'strategy: glob-url\n'
    'base_url: http://localhost:5173\n'
    'output_dir: docs/screenshots\n'
    'routes:\n'
    '  - {match: "src/pages/Login.*", url: /login, name: login}\n'
)


class TestCaptureHook:
    def test_no_config_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0

    def test_no_matching_target_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)
        assert screenshot_capture.main(['src/util.ts']) == 0

    def test_happy_path_writes_manifest_and_stages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)
        monkeypatch.setattr(
            screenshot_capture,
            'capture_targets',
            lambda targets, out, vp: [
                Shot(name=t.name, path=f'docs/screenshots/{t.name}.png', url=t.url)
                for t in targets
            ],
        )
        staged: list[list[str]] = []
        monkeypatch.setattr(screenshot_capture, 'git_add', lambda paths: staged.append(paths))
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0
        shots = read_manifest('docs/screenshots')
        assert [s.name for s in shots] == ['login']
        assert staged == [['docs/screenshots']]

    def test_browser_unavailable_skips_when_not_strict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)

        def boom(targets: object, out: object, vp: object) -> list[Shot]:
            raise runner.BrowserUnavailableError('no browser')

        monkeypatch.setattr(screenshot_capture, 'capture_targets', boom)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0

    def test_browser_unavailable_fails_when_strict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG + 'strict: true\n')

        def boom(targets: object, out: object, vp: object) -> list[Shot]:
            raise runner.BrowserUnavailableError('no browser')

        monkeypatch.setattr(screenshot_capture, 'capture_targets', boom)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_capture_hook.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_capture'`

- [ ] **Step 3: Write the implementation**

Create `pre_commit_hooks/screenshot_capture.py`:

```python
#!/usr/bin/python3
"""Hook to screenshot UI screens affected by staged files."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from pre_commit_hooks.screenshot_sync.capture import resolve_targets
from pre_commit_hooks.screenshot_sync.capture.runner import (
    BrowserUnavailableError,
    CaptureFailedError,
    capture_targets,
)
from pre_commit_hooks.screenshot_sync.config import load_config
from pre_commit_hooks.screenshot_sync.gitutil import git_add
from pre_commit_hooks.screenshot_sync.manifest import write_manifest
from pre_commit_hooks.screenshot_sync.reporting import skip_or_fail


def main(argv: Sequence[str] | None = None) -> int:
    """Capture screenshots for changed UI files and stage them."""
    parser = argparse.ArgumentParser(description='Screenshot UI screens for a commit.')
    parser.add_argument('filenames', nargs='*', help='Staged files (from pre-commit).')
    args = parser.parse_args(argv)

    config = load_config()
    if config is None:
        return 0

    targets = resolve_targets(config, list(args.filenames))
    if not targets:
        return 0

    try:
        shots = capture_targets(targets, config.output_dir, config.viewport)
    except (BrowserUnavailableError, CaptureFailedError) as exc:
        return skip_or_fail(config.strict, str(exc))

    write_manifest(config.output_dir, shots)
    git_add([config.output_dir])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_capture_hook.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_capture.py tests/test_screenshot_capture_hook.py
git commit -m "feat: add screenshot-capture hook"
```

---

### Task 9: `screenshot-publish` hook

**Files:**
- Create: `pre_commit_hooks/screenshot_publish.py`
- Test: `tests/test_screenshot_publish_hook.py`

**Interfaces:**
- Consumes: `load_config` (Task 1), `read_manifest` (Task 2), `update_readme_file` (Task 6), `notion.publish`/`notion.NotionError` (Task 7), `git_add` (Task 5), `skip_or_fail` (Task 5).
- Produces: `def main(argv: Sequence[str] | None = None) -> int`. `pass_filenames: false`, so argv is ignored.

**Orchestration:** no config → `return 0`. Empty manifest → `return 0`. If `readme.enabled` and `update_readme_file` reports a change → `git_add([readme.file])`. If `notion.enabled`: read `NOTION_API_KEY`; missing → `skip_or_fail`; on `NotionError` → `skip_or_fail`. Return the first non-zero `skip_or_fail` result, else `0`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_publish_hook.py`:

```python
"""Tests for the screenshot-publish hook orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks import screenshot_publish
from pre_commit_hooks.screenshot_sync.manifest import Shot, write_manifest
from pre_commit_hooks.screenshot_sync.publish import notion


def _config(tmp_path: Path, body: str) -> None:
    (tmp_path / '.screenshot-sync.yaml').write_text(body, encoding='utf-8')


_README_ONLY = (
    'strategy: glob-url\n'
    'output_dir: docs/screenshots\n'
    'publish:\n'
    '  readme: {enabled: true, file: README.md, marker: screenshots}\n'
    '  notion: {enabled: false}\n'
)


class TestPublishHook:
    def test_no_config_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert screenshot_publish.main([]) == 0

    def test_empty_manifest_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _config(tmp_path, _README_ONLY)
        assert screenshot_publish.main([]) == 0

    def test_readme_updated_and_staged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _config(tmp_path, _README_ONLY)
        (tmp_path / 'README.md').write_text('# Project\n', encoding='utf-8')
        write_manifest(
            'docs/screenshots',
            [Shot(name='login', path='docs/screenshots/login.png', url='/login')],
        )
        staged: list[list[str]] = []
        monkeypatch.setattr(screenshot_publish, 'git_add', lambda paths: staged.append(paths))
        assert screenshot_publish.main([]) == 0
        assert '![login](docs/screenshots/login.png)' in (tmp_path / 'README.md').read_text()
        assert staged == [['README.md']]

    def test_notion_missing_key_skips_when_not_strict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _config(
            tmp_path,
            'strategy: glob-url\noutput_dir: docs/screenshots\n'
            'publish:\n'
            '  readme: {enabled: false}\n'
            '  notion: {enabled: true, page_id: p1}\n',
        )
        write_manifest('docs/screenshots', [Shot(name='a', path='a.png', url='/a')])
        monkeypatch.delenv('NOTION_API_KEY', raising=False)
        monkeypatch.setattr(screenshot_publish, 'git_add', lambda paths: None)
        assert screenshot_publish.main([]) == 0

    def test_notion_published_when_key_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _config(
            tmp_path,
            'strategy: glob-url\noutput_dir: docs/screenshots\n'
            'publish:\n'
            '  readme: {enabled: false}\n'
            '  notion: {enabled: true, page_id: p1, image_base_url: https://cdn/x}\n',
        )
        write_manifest('docs/screenshots', [Shot(name='a', path='a.png', url='/a')])
        monkeypatch.setenv('NOTION_API_KEY', 'tok')
        calls: dict[str, object] = {}
        monkeypatch.setattr(
            notion,
            'publish',
            lambda page_id, shots, token, image_base_url: calls.update(
                {'page_id': page_id, 'token': token}
            ),
        )
        assert screenshot_publish.main([]) == 0
        assert calls == {'page_id': 'p1', 'token': 'tok'}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_screenshot_publish_hook.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pre_commit_hooks.screenshot_publish'`

- [ ] **Step 3: Write the implementation**

Create `pre_commit_hooks/screenshot_publish.py`:

```python
#!/usr/bin/python3
"""Hook to publish captured screenshots to the README and/or Notion."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from pre_commit_hooks.screenshot_sync.config import load_config
from pre_commit_hooks.screenshot_sync.gitutil import git_add
from pre_commit_hooks.screenshot_sync.manifest import read_manifest
from pre_commit_hooks.screenshot_sync.publish import notion
from pre_commit_hooks.screenshot_sync.publish.readme import update_readme_file
from pre_commit_hooks.screenshot_sync.reporting import skip_or_fail


def main(argv: Sequence[str] | None = None) -> int:
    """Publish the manifest's screenshots to the configured destinations."""
    parser = argparse.ArgumentParser(description='Publish captured screenshots.')
    parser.add_argument('filenames', nargs='*', help='Ignored (pass_filenames: false).')
    parser.parse_args(argv)

    config = load_config()
    if config is None:
        return 0

    shots = read_manifest(config.output_dir)
    if not shots:
        return 0

    if config.publish.readme.enabled:
        readme_cfg = config.publish.readme
        if update_readme_file(readme_cfg.file, shots, readme_cfg.marker):
            git_add([readme_cfg.file])

    if config.publish.notion.enabled:
        notion_cfg = config.publish.notion
        token = os.environ.get('NOTION_API_KEY')
        if not token:
            return skip_or_fail(config.strict, 'NOTION_API_KEY is not set; skipping Notion')
        try:
            notion.publish(notion_cfg.page_id, shots, token, notion_cfg.image_base_url)
        except notion.NotionError as exc:
            return skip_or_fail(config.strict, str(exc))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshot_publish_hook.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add pre_commit_hooks/screenshot_publish.py tests/test_screenshot_publish_hook.py
git commit -m "feat: add screenshot-publish hook"
```

---

### Task 10: Wire entry points, hook definitions, and docs

**Files:**
- Modify: `pyproject.toml` (the `[project.scripts]` table)
- Modify: `.pre-commit-hooks.yaml` (append two entries)
- Modify: `README.md` (document the two hooks)

**Interfaces:**
- Consumes: `screenshot_capture:main`, `screenshot_publish:main` (Tasks 8–9).
- Produces: installable console scripts `screenshot-capture` / `screenshot-publish`, and pre-commit hook ids `screenshot-capture` / `screenshot-publish`.

- [ ] **Step 1: Add the console scripts to `pyproject.toml`**

In `pyproject.toml`, under `[project.scripts]`, add these two lines after the existing `makefile-check = ...` line:

```toml
screenshot-capture = "pre_commit_hooks.screenshot_capture:main"
screenshot-publish = "pre_commit_hooks.screenshot_publish:main"
```

- [ ] **Step 2: Verify the entry points import**

Run: `pip install -e . && python -c "from pre_commit_hooks.screenshot_capture import main as c; from pre_commit_hooks.screenshot_publish import main as p; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Append the hook definitions to `.pre-commit-hooks.yaml`**

Append to the end of `.pre-commit-hooks.yaml`:

```yaml
- id: screenshot-capture
  additional_dependencies:
    - playwright
    - PyYAML
  description: screenshot UI screens affected by staged files (Playwright; gracefully skips if unavailable)
  entry: screenshot-capture
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: capture screenshots of changed UI screens
  pass_filenames: true
  stages: [pre-commit]
  types_or: ["ts", "tsx", "javascript", "jsx", "css", "file"]
- id: screenshot-publish
  additional_dependencies:
    - requests
    - PyYAML
  description: publish captured screenshots to README and/or Notion from the manifest
  entry: screenshot-publish
  language: python
  minimum_pre_commit_version: '4.1.0'
  name: publish screenshots to README/Notion
  pass_filenames: false
  stages: [pre-commit]
```

- [ ] **Step 4: Validate the hooks YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.pre-commit-hooks.yaml')); print('ok')"`
Expected: prints `ok`

- [ ] **Step 5: Document the hooks in `README.md`**

Add a new subsection under the existing "Hooks available" list. Insert this block immediately before the closing of that section (after the last documented hook):

````markdown
### screenshot-capture / screenshot-publish

Capture screenshots of the UI screens affected by a commit and publish them to
the README and/or a Notion page. Two composable hooks linked by a manifest.

```yaml
- repo: https://github.com/chrysa/pre-commit-tools
  rev: v0.0.34
  hooks:
    - id: screenshot-capture
    - id: screenshot-publish
```

Add a `.screenshot-sync.yaml` to the consuming repo (absent → both hooks are
no-ops):

```yaml
strategy: glob-url            # glob-url | storybook | fixed-routes
base_url: http://localhost:5173
output_dir: docs/screenshots
viewport: { width: 1280, height: 800 }
strict: false                # true = blocking on failure; false = warn + skip
routes:
  - { match: "src/pages/Login.*", url: /login, name: login }
publish:
  readme: { enabled: true, file: README.md, marker: screenshots }
  notion: { enabled: false, page_id: "", image_base_url: "" }   # NOTION_API_KEY via env
```

`screenshot-capture` renders the routes whose source files changed (Playwright),
writes PNGs + a manifest under `output_dir`, and stages them. `screenshot-publish`
reads the manifest and updates the README section between
`<!-- screenshots:start -->` / `<!-- screenshots:end -->` and/or appends image
blocks to the Notion page. By default neither hook blocks the commit; set
`strict: true` to make environment/network failures blocking. Playwright browser
binaries are not auto-installed — run `playwright install chromium` once per repo.
````

- [ ] **Step 6: Run the full test suite for the new modules**

Run: `python -m pytest tests/test_screenshot_config.py tests/test_screenshot_manifest.py tests/test_screenshot_capture_targets.py tests/test_screenshot_runner.py tests/test_screenshot_gitutil.py tests/test_screenshot_readme.py tests/test_screenshot_notion.py tests/test_screenshot_capture_hook.py tests/test_screenshot_publish_hook.py -v`
Expected: PASS (all screenshot-sync tests green)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .pre-commit-hooks.yaml README.md
git commit -m "feat: wire screenshot-capture/publish entry points and docs"
```

---

## Self-Review

**Spec coverage:**
- Two composable hooks + manifest interface → Tasks 8, 9, 2. ✓
- Configurable strategy (glob-url / storybook / fixed-routes) → Task 3. ✓
- Playwright capture → Task 4. ✓
- README + Notion publishers, each toggleable → Tasks 6, 7, 9. ✓
- Auto `git add` of generated files → Task 5 + Tasks 8, 9. ✓
- Defensive skip vs `strict` → Task 5 (`skip_or_fail`) used in Tasks 8, 9. ✓
- Config absent → no-op → Tasks 8, 9 (`load_config` returns None). ✓
- Graceful-skip paths (browser missing, server unreachable, Notion key missing) → Tasks 4, 8, 9. ✓
- File layout from spec → matched in "File Structure". ✓
- Entry points + `.pre-commit-hooks.yaml` + deps → Task 10. ✓
- Tests with Playwright + requests mocked → Tasks 4, 7. ✓

**Refinement vs spec:** the Notion config gained an `image_base_url` field (not in the original spec) because the Notion API cannot host local PNGs — image blocks need an external URL. Without it, the publisher falls back to text blocks. This is an honest, minimal addition documented in Task 7 and the README.

**Placeholder scan:** no TBD/TODO; every code step shows complete code. ✓

**Type consistency:** `Shot(name, path, url)`, `CaptureTarget(name, url, full_url)`, `resolve_targets(config, changed_files)`, `capture_targets(targets, output_dir, viewport)`, `update_readme_file(file, shots, marker)`, `notion.publish(page_id, shots, token, image_base_url)`, `skip_or_fail(strict, message)`, `git_add(paths)` — names and signatures are consistent across producing and consuming tasks. ✓
