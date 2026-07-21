# CLAUDE.md — pre-commit-tools

> @[claude-sonnet-4-6]
A collection of [pre-commit](https://pre-commit.com) hooks for code quality checks (Python, TypeScript/JS, CSS, Django/FastAPI, Docker, Config).

> **GitHub Copilot**: also read `.github/copilot-instructions.md` and all files under `.github/instructions/` for the full coding conventions.

---

## Commands

All checks go through `make` targets — never invoke `ruff`/`pytest`/`mypy` directly on the host
outside the make wrapper. Ruff config lives in `config-tools/ruff.toml`.

```bash
make install-dev        # Editable install with all extras + dev tooling
make quality            # lint + format-check + typecheck
make test               # All tests
make test-fail-fast     # Stop on first failure
make test-cov           # Tests with coverage report
make pre-commit         # Run all pre-commit hooks on every file

# Validate GitHub Actions workflows (requires actionlint)
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest
```

- **Regression gate (before every PR)**: `make quality && make test-cov`.
- **Single test**: `pytest tests/test_my_hook.py -v`.
- `pip install -e .` is REQUIRED before `pre-commit run` — hook entry points must be importable.

---

## Architecture

```
pre_commit_hooks/          # hook implementations
    tools/
        logger.py              # structured logger
        pattern_detection.py   # base class for regex-based hooks
        pre_commit_tools.py    # shared argument parsing (PreCommitTools)
        update_readme.py       # README auto-update utility
tests/                     # one file per hook (test_<slug>.py)
config-tools/              # ruff.toml, bandit.yaml, black.toml…
.pre-commit-hooks.yaml     # hook manifest (for consumers of this repo)
setup.cfg                  # entry points + dependencies + mypy/pytest config
```

---

## Creating a new hook

1. `pre_commit_hooks/my_hook.py` — implement the logic
2. `setup.cfg` — add the entry point under `[options.entry_points] console_scripts`
3. `.pre-commit-hooks.yaml` — register the hook
4. `tests/test_my_hook.py` — write tests
5. `README.md` — update the hooks table

---

## Python conventions (non-negotiable)

- **`from __future__ import annotations`** — at the top of every Python file
- **Python 3.12+** — `list[str]`, `str | None`, `dict[str, int]` (PEP 585/604), never `List`, `Optional`, `Union`
- **Full annotations** — all public functions must be typed (Ruff `ANN` rules)
- **Mandatory `main()` signature**:
  ```python
  def main(argv: Sequence[str] | None = None) -> int:
  ```
- **`PreCommitTools`** — use `tools/pre_commit_tools.py` instead of inline `argparse`
- **`Path.read_text(encoding='utf-8')`** — never use `open()` directly

## Test conventions

- `_write(tmp_path, name, content)` — helper to create temporary files
- Content with `\n` — never use multiline triple-quotes
- Classes `TestMyFunction` + `TestMyHookMain` — group tests by scenario
- `@pytest.mark.parametrize` — for multiple inputs on the same function

---

## Ruff — zero tolerance

```bash
ruff check --config=config-tools/ruff.toml pre_commit_hooks tests
ruff format --check --config=config-tools/ruff.toml pre_commit_hooks
```

Every `# noqa` must include the rule code and a justification:
```python
result: Any = ext.call()  # noqa: ANN401 — third-party untyped API
```

---

## Known pitfalls

| Problem | Solution |
|---|---|
| `Executable print-detection not found` in CI | Add `pip install -e .` before `pre-commit/action` |
| `reorder-python-imports` vs `ruff-format` (infinite loop) | **Do not use** `reorder-python-imports` — ruff handles imports via rule `I` |
| `python-no-log-warn` false positives on Python strings containing `.warn(` | Exclude the file in `.pre-commit-config.yaml` |
| Pushing to `chrysa/pre-commit-tools` | `chrysa` account required: `gh auth switch --user chrysa` + token injection in URL |
| Merge blocked by branch protection | `gh pr merge <n> --admin` |

---

## CI/CD

- **GitHub Actions**: `.github/workflows/ci.yml` — jobs `version`, `lint`, `test`, `sonar`
- **Matrix**: Python 3.12, 3.13, 3.14
- **Pre-commit workflow**: `.github/workflows/pre-commit.yml` — must have `pip install -e .` before `pre-commit/action@v3.0.1`
- **SonarCloud**: `sonar-project.properties` — requires secret `SONAR_TOKEN`
- **detect-secrets**: baseline in `.secrets.baseline` — regenerate with `detect-secrets scan > .secrets.baseline` if real test secrets are added

---

## Optional extras required per hook

| Extra | Hooks |
|---|---|
| `yaml` | `yaml-sorter` |
| `format_dockerfile` | `format-dockerfiles` |
| `dead_code` | `python-dead-code` (vulture) |
| `ts_unreachable_code` | `ts-unreachable-code-detection` (tree-sitter) |
| `pylint_report` | `pylint-report-html` |

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **pre-commit-tools** (1214 symbols, 2689 relationships, 94 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/pre-commit-tools/context` | Codebase overview, check index freshness |
| `gitnexus://repo/pre-commit-tools/clusters` | All functional areas |
| `gitnexus://repo/pre-commit-tools/processes` | All execution flows |
| `gitnexus://repo/pre-commit-tools/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->


<!-- chrysa:standards:start · managed by distribute-standards.sh · DO NOT EDIT -->
# chrysa — Transverse Standards

These conventions are identical across every chrysa repo. Repo-specific rules live in the
local `CLAUDE.md`; this file is the shared baseline imported by it.

## Cross-cutting stack (settled ADRs — do not relitigate)

| Layer            | Decision                                                        |
|------------------|----------------------------------------------------------------|
| Python           | 3.14 target (CI matrix 3.12 + 3.14)                            |
| FastAPI          | >= 0.115 + Pydantic v2                                          |
| Frontend         | React 19 + TypeScript + Vite 6                                  |
| UI               | shadcn/ui + Tailwind CSS                                        |
| State            | TanStack Query + Zustand                                        |
| DB               | PostgreSQL 16 + Redis 7                                         |
| ORM              | SQLAlchemy 2.0 async + Alembic                                  |
| Auth             | 4 modes: Google OAuth2 · local (bcrypt) · LDAP · VCS OAuth      |
| i18n             | react-i18next + fastapi-babel · FR + EN from V1                 |
| Monorepo         | Turborepo + pnpm workspaces                                     |
| Versioning       | GitVersion (semantic auto — never bump manually)               |
| Quality CI       | SonarCloud (0 hotspot · rating A)                               |
| Linting          | Ruff + Mypy (Python) · ESLint (TS)                             |
| Pre-commit       | detect-secrets + ruff + mypy + commitlint                      |
| Error handling   | withErrorHandling() → auto GitHub Issue on failure             |
| Hosting          | Kimsufi · Docker Compose (local) · Nginx · Certbot · Tailscale  |
| Monitoring       | Sentry + Uptime Kuma (self-hosted)                            |
| Agents           | Claude API (primary) · Ollama (fallback)                       |
| Orchestration    | LangGraph (stateful) · PydanticAI (structured outputs)         |

## Non-negotiable conventions

- **Language**: English — all code, comments, docs, instructions, and config files.
- **Commits**: Conventional Commits (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`).
- **Branches**: `feature/`, `bugfix/`, `chore/`, `hotfix/`, `release/` · default branch `develop`.
- **Merge**: squash merge only · force push forbidden · auto-merge requires CI + owner.
- **One PR per issue**, scoped tight. Every PR references an issue (`Closes/Fixes/Refs #N`).
  Exception: label `hotfix`. The `enforce-issue-link` workflow is a blocking status check.
- **Dark mode** mandatory from V1. **Accessibility** WCAG 2.1 AA.
- **Notion logging**: every advancement and modification (progress, decisions, state
  changes) is logged in Notion — the single source of truth. Run `@notion-sync` after any
  state change; in case of conflict between local docs and Notion, Notion wins.
- **No hardcoded constants** in code — neither backend (Python) nor frontend (TS).
  All constants and config values (thresholds, business rules, labels, URLs, magic
  numbers) live in **external YAML files** and are loaded at runtime. Code reads them
  through a typed loader (Pydantic Settings backend · generated typed module frontend),
  never as inline literals. Only language-level enums (e.g. `status.HTTP_*`) are exempt.
- **Semantic URLs & code** — URLs are resource-oriented and human-readable: lowercase,
  hyphenated, plural-noun collections, no verbs or actions in the path (`GET /invoices/42`,
  never `/getInvoice?id=42`); REST shapes follow the `api-design` skill. Code is
  self-describing: intention-revealing names over comments, semantic HTML elements
  (`<nav>`, `<button>`, `<main>`, `<header>`…) never a `<div>` wired as a control, and
  ARIA used only to fill gaps native semantics cannot express.

## Quality gates

- Test coverage **>= 85%** by default. A repo may override upward, never below 80%.
- Lint warnings: **0**. Mypy clean. SonarCloud rating **A**, 0 security hotspot.
- Max function lines 50 · max file lines 500 · cyclomatic complexity heuristic <= 10.

## Makefile targets

- **Referential**: `Forge-Stack-Workshop/base-makefile` (`Makefile.basic`, `Makefile.python`,
  `Makefile.with-sub-folder`) is the single source of truth for target names and behaviour.
- **Canonical naming** — follow base-makefile verbatim, one word where it is one word:
  `typecheck` (**never** `type-check`), `test-cov`, `format-check`, `quality-gate-verify`,
  `docker-test`, `ci`. Renaming or aliasing a canonical target is forbidden.
- **Mandatory socle** — every application repo MUST expose, with these exact names and intent:
  `help install install-dev lint format format-check typecheck test test-cov pre-commit clean
  ci quality-gate-baseline quality-gate-verify`. Non-applicative repos (pure infra/Helm/Terraform,
  config-only, docs) are exempt from the language-specific targets (`typecheck`, `test-cov`) but
  still expose `help lint pre-commit clean`.
- **Docs must match** — every `make <target>` cited in `CLAUDE.md` or `README.md` MUST exist in
  the Makefile (no `make type-check` when the target is `typecheck`).
- **Recipe style** — prefix every recipe line with `@`; add `## Description` after each target so
  it appears in `make help`.

## Shared skills (load on demand from shared-standards/.claude/skills/)

- `testing-pytest` — pytest DDD + pytest-mock + constants (writing tests)
- `dockerfile-multistage` — 4-stage Python 3.14 containers (editing Dockerfile)
- `api-design` — REST standards + FastAPI patterns (designing endpoints)
- `async-patterns` — async FastAPI + SQLAlchemy async sessions (async code)
- `clean-architecture` — FastAPI module/layer structure (adding a feature)
- `error-handling` — FastAPI errors + Sentry + logging (handling errors)
- `contract-testing` — library contract / breaking-change tests (@chrysa/* releases)
- `agent-patterns` — LangGraph + PydanticAI + Claude API (building agents)
- `ui-ux` — UX/UI/ergonomics + WCAG 2.1 AA + dark mode + i18n (human-facing surfaces)

## Error handling pattern (all automations)

```text
try:    fn()
except: gh issue create --title "[chrysa] failure" --label "chrysa-error"
```

## Observability — Sentry → GitHub issues (norm)

Every status:dev repo ships a Sentry project, and **a new Sentry issue automatically opens a
GitHub issue** via Sentry's native GitHub integration. No relay, no PAT in the repo — the
integration owns the link, so a Sentry issue maps to exactly one GitHub issue (no duplicates).

Mechanism: a per-project Sentry **issue alert rule** with
condition `FirstSeenEventCondition` (a new issue is created) and action
`GitHubCreateTicketAction` targeting `chrysa/<repo>`, labels `sentry`, `bug`.
Provision it across all projects with
`shared-standards/scripts/sentry-github-issues.sh` (idempotent, `--dry-run` first).

Per-project activation checklist:

1. Org GitHub integration installed once in Sentry (Settings → Integrations → GitHub) with
   access to the chrysa repos.
2. The repo has a Sentry project whose slug matches the repo name.
3. The auto-issue alert rule exists (run the provisioning script, or add it in
   Alerts → Create Alert → Issues → action "Create a GitHub issue").
4. The GitHub repo has a `sentry` label (CI label sync provides it).
<!-- chrysa:standards:end -->
