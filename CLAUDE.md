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
ruff check --config=config-tools/ruff.toml pre_commit_hooks tests
ruff format --config=config-tools/ruff.toml pre_commit_hooks

# Type-checking
mypy --config-file=setup.cfg pre_commit_hooks

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
