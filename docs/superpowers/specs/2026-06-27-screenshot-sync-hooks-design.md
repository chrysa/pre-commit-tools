# Design — Screenshot-sync pre-commit hooks

**Date:** 2026-06-27
**Project:** `pre-commit-tools`
**Status:** Approved (brainstorming) — ready for implementation plan

## Goal

Add the ability to capture screenshots of UI screens affected by a commit and
publish them to the repository `README.md` and/or a Notion page. Delivered as
two composable pre-commit hooks living in the existing `pre-commit-tools`
package.

## Decisions (from brainstorming)

- **Trigger:** real `pre-commit` stage, runs on every commit. Designed
  defensively: by default it **never blocks the commit** — on any environment or
  network problem it warns and exits 0. A `strict: true` config flag makes those
  cases blocking.
- **Capture:** parametrable `strategy` — one of `glob-url`, `storybook`,
  `fixed-routes`. Rendering is done with Playwright.
- **Destination:** README **and** Notion, each independently toggleable in
  config.
- **Staging:** the hooks `git add` the files they generate so the commit
  succeeds on the first try with the screenshots included.
- **Architecture:** approach **B** — two composable hooks
  (`screenshot-capture` + `screenshot-publish`) connected by a manifest file as
  their well-defined interface.

## Architecture — two chained hooks

Two distinct entry points in `pre_commit_hooks/`, both declared
`stages: [pre-commit]`. Order is controlled by the consuming repo's
`.pre-commit-config.yaml` (capture must be listed before publish).

- **`screenshot-capture`**
  - Input: staged changed files (`pass_filenames: true`).
  - Loads `.screenshot-sync.yaml`; if absent → no-op (exit 0).
  - Maps changed files → capture targets according to `strategy`.
  - Renders each target with Playwright, writes PNGs to `output_dir`.
  - Writes/updates the **manifest**.
  - `git add` of `output_dir`.

- **`screenshot-publish`**
  - Loads the same config + the manifest (only reads it).
  - If `publish.readme.enabled`: regenerates the README screenshots section,
    `git add README.md`.
  - If `publish.notion.enabled`: uploads the manifest's shots to a Notion page
    via the Notion REST API.

**Interface = the manifest** `docs/screenshots/.screenshot-manifest.json` (path
relative to `output_dir`):

```json
{ "shots": [ { "name": "login", "path": "docs/screenshots/login.png", "url": "/login" } ] }
```

Only `capture` writes the manifest; only `publish` reads it. This keeps each hook
independently testable — capture needs no network, publish needs no browser.

## Config `.screenshot-sync.yaml` (in the consuming repo)

Absent file → both hooks are silent no-ops (safety for non-UI repos).

```yaml
strategy: glob-url            # glob-url | storybook | fixed-routes
base_url: http://localhost:5173
output_dir: docs/screenshots
viewport: { width: 1280, height: 800 }
strict: false                # true = blocking failures; false = warn + exit 0

routes:                      # strategy: glob-url
  - { match: "src/pages/Login.*", url: /login, name: login }
fixed_routes:                # strategy: fixed-routes
  - { url: /, name: home }
storybook:                   # strategy: storybook
  url: http://localhost:6006
  stories:
    - { match: "src/components/Button.*", id: "components-button--primary", name: button }

publish:
  readme: { enabled: true, file: README.md, marker: screenshots }
  notion: { enabled: false, page_id: "" }   # NOTION_API_KEY via env
```

README injection happens between
`<!-- screenshots:start -->` / `<!-- screenshots:end -->` markers, created if
missing. The marker name is configurable via `publish.readme.marker`.

### Strategy semantics

- **glob-url:** for each staged file matching a `routes[].match` glob, capture
  `base_url + url` → `output_dir/<name>.png`.
- **fixed-routes:** if **any** staged file matches a configured UI extension,
  capture every entry of `fixed_routes` (ignores which file changed).
- **storybook:** for each staged file matching a `storybook.stories[].match`
  glob, capture `storybook.url/iframe.html?id=<id>` → `<name>.png`.

## Data flow & error handling (defensive)

`capture`: staged files → filter by `match` → resolve URLs → Playwright
screenshot → PNG + manifest → `git add output_dir`.

`publish`: manifest → if `readme.enabled` regenerate section + `git add` README;
if `notion.enabled` upload shots via REST.

Graceful skip (warn, **exit 0**) when:

- config file absent;
- Playwright or its browser binary not installed;
- dev-server / Storybook URL unreachable;
- `NOTION_API_KEY` missing while `notion.enabled` (skips Notion only).

`strict: true` turns each of these into a blocking failure (exit 1). Default
`strict: false` never blocks the commit, matching the "real pre-commit, every
commit" choice.

## File layout & tests

```
pre_commit_hooks/
  screenshot_capture.py        # main() + orchestration
  screenshot_publish.py        # main() + orchestration
  screenshot_sync/
    __init__.py
    config.py                  # load + validate .screenshot-sync.yaml
    manifest.py                # read/write manifest
    capture/
      __init__.py
      glob_url.py              # one strategy = one module
      storybook.py
      fixed_routes.py
      runner.py                # Playwright wrapper + browser detection
    publish/
      __init__.py
      readme.py                # marker injection
      notion.py                # Notion REST API
    gitutil.py                 # git add wrapper
```

- `.pre-commit-hooks.yaml`: two entries.
  - `screenshot-capture`: `additional_dependencies: [playwright, PyYAML]`,
    `pass_filenames: true`, `stages: [pre-commit]`,
    `types_or: [ts, tsx, javascript, jsx, css, file]`.
  - `screenshot-publish`: `additional_dependencies: [requests, PyYAML]`,
    `pass_filenames: false`, `stages: [pre-commit]`.
- `pyproject.toml`: two `project.scripts`
  (`screenshot-capture`, `screenshot-publish`).

### Tests (pytest, existing repo pattern)

Playwright and `requests` are **mocked** — no browser or network in CI.

- config loading + validation (valid, missing, malformed, unknown strategy);
- strategy mapping for each of the three strategies;
- manifest round-trip (write then read);
- README marker injection (markers present, markers absent → created,
  re-run idempotent);
- Notion payload construction (mocked `requests`);
- git stager (mocked `subprocess`);
- every graceful-skip path (config absent, browser missing, server unreachable,
  Notion key missing) — assert exit 0 and warning; assert exit 1 under
  `strict: true`.

## Out of scope (YAGNI)

- Launching the dev server / Storybook itself (assumed already running, else
  graceful skip).
- Image diffing / visual regression.
- Destinations other than README and Notion.
- Auto-installing Playwright browser binaries.
