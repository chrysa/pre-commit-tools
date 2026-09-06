# CLAUDE.md — pre-commit-tools

> @[claude-sonnet-4-6]
A collection of [pre-commit](https://pre-commit.com) hooks for code quality checks (Python, TypeScript/JS, CSS, Django/FastAPI, Docker, Config).

> **GitHub Copilot**: also read `.github/copilot-instructions.md` and all files under `.github/instructions/` for the full coding conventions.

---

## Essential commands

```bash
# Full dev installation
pip install -e ".[format_dockerfile,yaml,dead_code]"
pip install ruff mypy pylint pytest pytest-cov build twine

# Linting / formatting
ruff check pre_commit_hooks tests
ruff format pre_commit_hooks

# Type-checking
mypy --config-file=pyproject.toml pre_commit_hooks

# Tests
pytest                             # all tests
pytest tests/test_my_hook.py -v   # single file
pytest --failed-first -x          # stop on first failure

# Pre-commit (on all files)
pip install -e .                   # REQUIRED before pre-commit run
pre-commit run --all-files

# Makefile shortcuts
make install-dev
make quality    # lint + format-check + type-check
make test
make test-cov
```

---

## Local test procedure

All checks must go through `make` targets. Never invoke `ruff`/`pytest`/`mypy` directly on the host outside of the make wrapper.

```bash
# 1. Install
make install-dev

# 2. Full quality check (lint + format + type-check)
make quality

# 3. Run tests
make test                  # all tests
make test-fail-fast        # stop on first failure
make test-cov              # with coverage report

# 4. Run all pre-commit hooks on every file
make pre-commit

# 5. Validate GitHub Actions workflows (requires actionlint)
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest
```

### Regression gate (before every PR)
```bash
make quality && make test-cov
# Coverage must stay >= 85%. Lint warnings must be 0.
```

---


## Language Rules

- Language: English — all code, comments, documentation, instructions, and configuration files must be in English.
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
ruff check pre_commit_hooks tests
ruff format --check pre_commit_hooks
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

## Compact instructions

When compacting, always preserve:
1. List of all files modified this session (with paths)
2. Current task description and next steps
3. Any uncommitted / unpushed changes
4. Open blockers and errors not yet resolved

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

## Skills

Shared skills from `shared-standards/.claude/skills/`:

- `ui-ux/SKILL.md` — UX/UI/ergonomics across ALL surfaces (web, CLI, VS Code, Discord, desktop, game, agent) + WCAG 2.1 AA + dark mode + i18n FR+EN (load when building any human-facing surface)


<!-- chrysa:standards:start · managed by distribute-standards.sh · DO NOT EDIT -->
# chrysa — Transverse Standards (core)

> The **slim always-on core**. The canonical, tool-agnostic source of truth is `standards/STANDARDS.chrysa.md`; the normative annexes live under `standards/annexes/`. Each rule below is a one-line pointer — its full text lives in the per-domain file named beside the heading (`standards/rules/<domain>.md`), read on demand.

**Where an annexe and the canon disagree, the canon wins.**

### Governance, language & compliance · `standards/rules/governance.md`
- Normative annexes
- Language
- Compliance targets
- Governance — strategic pillars & ADR format

### Cross-cutting stack · `standards/rules/stack.md`
- Cross-cutting stack (settled ADRs — do not relitigate)

### SCM — branches, commits & pull requests · `standards/rules/scm.md`
- Commits
- Branches
- Branch model — `main` is production, `develop` is the workspace
- Merge
- One PR per issue
- Issues and PRs are type-driven

### Architecture, decoupling & portability · `standards/rules/architecture.md`
- Repo provenance — every code repo depends on `project-init`
- Every repo declares its profile and DDD level
- Projects talk through versioned contracts only
- Everything is machine-agnostic and portable — no rule, repo, or script is bound to one machine
- Every external server the service talks to is addressed through the environment — never hardcoded
- Every tracked file and folder must earn its place — a repo holds only what is useful to it now
- The repository architecture is legible to an agent — optimised for Claude, not only for humans
- Deferred work is a governed job, not a fire-and-forget

### Testing · `standards/rules/testing.md`
- Tests: pytest only
- Frontend tests: Vitest + Testing Library + MSW — from the scaffold, not later

### Frontend & web semantics · `standards/rules/frontend.md`
- TypeScript is strict by contract
- The JS/TS package manager is `pnpm` — `npm` and `yarn` are forbidden
- React is a presentation layer, not the domain
- The frontend says when the backend is unreachable or unstable
- The frontend is reactive and real-time by default
- UI state survives reload & focus
- Everything is semantic — the markup, the data, and the URLs
- URL-addressable frontend navigation — mandatory

### APIs, contracts & real-time · `standards/rules/api.md`
- A real-time backend has channel contracts and never blocks
- APIs, SDKs & public contracts follow the `STD-API-001` contract

### Accessibility · `standards/rules/accessibility.md`
- Dark mode
- Every site is usable by the majority of disabilities — not only the screen-reader case

### Documentation & session state · `standards/rules/docs.md`
- Notion logging
- Documentation and Notion are maintained in lockstep with the code — a change that leaves them stale is unfinished
- Session lifecycle (primer + memory + hindsight)

### AI agents & features · `standards/rules/agents.md`
- Agent actions are governed
- An AI feature is evaluated, not just shipped
- An agent writes only where the owner owns

### Security, identity & sessions · `standards/rules/security.md`
- Per-person data implies a user account — no exceptions dressed up as simplicity
- Identity goes through the cluster SSO first
- Rights are resolved against the common directory (LDAP), never re-declared per service
- A session is secured and it expires
- Every form is a hostile input surface — validate on the server, always
- Security scanning is a gate, not an afterthought — it runs in pre-commit and in CI

### Code quality & anti-patterns · `standards/rules/code-quality.md`
- No hardcoded constants
- No literal HTTP status codes — use the constants the framework already ships
- No code duplication — the second occurrence is an extraction order
- Raised errors are typed
- Failures are contained, and observable
- Prefer a lookup table to a state machine
- Decompose into small, independently unit-testable methods
- Code is read far more often than it is written — optimise for the reader, and standardise the form
- Avoid lambdas and anonymous constructs — a named function is the default
- Basic optimisations and known anti-patterns are caught in review and in CI
- A cache is a correctness contract, not a sprinkle of speed
- Quality gates
- Error handling pattern (all automations)

### Backend Python · `standards/rules/backend-python.md`
- Python packaging — `pyproject.toml` is the single source of truth
- Python is written object-oriented, one class per file
- Import the item, not the module — `from x import y; y()`
- Functions and methods are called with named arguments — positional call sites are the exception, not the rule

### Data, persistence & migrations · `standards/rules/data.md`
- Data, persistence & migrations follow the `STD-DATA-001` contract

### Observability & operations · `standards/rules/observability.md`
- Observability & production readiness follow the `STD-OPS-001` contract
- The container is versioned separately from the application it hosts, and an admin can see what is actually deployed
- Observability — error-tracking → GitHub issues (norm)

### Containers & compose · `standards/rules/containers.md`
- Everything runs in a container — the only exception is the slice of a repo genuinely bound to the host OS
- External dependencies are installed in containers, never on the host
- No virtualenv in a repo — ever
- Tool caches & deps never touch the project tree
- Dockerfiles are multi-stage, with a `production` and a `dev` stage — mandatory
- App containers ship the app only — the platform layer is the owner's responsibility
- Only a publicly useful port is published — everything else stays on the container network
- A compose file is minimal — declare only what the stack needs, default the rest
- Dev stage must hot-reload
- Local dev runs the code in-container, live, in debug mode — never the production server
- Default to dev mode when starting an app locally — any other mode only when explicitly asked
- `.dockerignore` mandatory & exhaustive
- Container-runtime policy

### Product surfaces · `standards/rules/product.md`
- Setup wizard & config panel
- A game is DRM-free and fully playable solo offline
- Every product that is operated ships a management backoffice
- If a user can supply a file, the product accepts an upload
- A floating assistant where it earns its place — never as decoration

### Design system · `standards/rules/design.md`
- Design system

### Developer loop & tooling · `standards/rules/dev-loop.md`
- Makefile targets
- Shared skills (load on demand from shared-standards/.claude/skills/)

### CI/CD, pre-commit & release · `standards/rules/ci-cd.md`
- Release & changelog config (canonical)
- GitHub Actions (reuse first · custom actions centralised · thin workflows)
- Pre-commit & git hooks (native, via pre-commit.com — never wrapped in make)
<!-- chrysa:standards:end -->
