# Decisions (ADR log) — pre-commit-tools

Architecture decisions reconstructed from the repo. These are **reverse-engineered
ADRs** — the original rationale is INFERENCE unless a source states it. Where a
chrysa-wide ADR governs (e.g. D-0012 context files), it is referenced, not restated.
Status is **Accepted** for anything currently in force in the tree.

---

## ADR-001 — One hook = one module + one entry point + one test file
- **Status:** Accepted (FACT — observed structure)
- **Context:** ~82 independent checks must stay individually toggmable by consumers.
- **Decision:** Each hook is `pre_commit_hooks/<slug>.py` with a `main(argv) -> int`,
  a console script in `pyproject.toml [project.scripts]`, a manifest id in
  `.pre-commit-hooks.yaml`, and `tests/test_<slug>.py`.
- **Consequences:** Uniform, trivially composable; adding a hook is a 5-step checklist
  (CLAUDE.md "Creating a new hook").

## ADR-002 — Shared base for pattern hooks
- **Status:** Accepted (FACT)
- **Decision:** Regex/detection hooks build on `tools/pattern_detection.py`; argument
  parsing goes through `tools/pre_commit_tools.py` (`PreCommitTools`) rather than
  inline `argparse`.
- **Consequences:** Consistent CLI and reporting; less duplication.

## ADR-003 — Python 3.14 baseline
- **Status:** Accepted (FACT — `pyproject.toml`, `Dockerfile.test`, `ci.yml`)
- **Decision:** `requires-python = ">=3.14"`; CI and the test image run 3.14 only.
- **Consequences:** Modern typing; consumers on older interpreters cannot install
  directly. **Note:** CLAUDE.md/README still mention a 3.12–3.14 matrix — stale (see
  REVIEW.md / CON-022).

## ADR-004 — setuptools build backend, `pyproject.toml` single source of truth
- **Status:** Accepted (FACT)
- **Decision:** `setuptools>=72` + `wheel`; no `setup.py`/`setup.cfg` as the source of
  truth (a `no_setup_files` hook even enforces this pattern for consumers).
- **Note:** CLAUDE.md references `setup.cfg` for entry points — stale; entry points now
  live in `pyproject.toml [project.scripts]` (see REVIEW.md).

## ADR-005 — Optional heavy tooling behind extras
- **Status:** Accepted (FACT)
- **Decision:** vulture (`dead_code`), tree-sitter (`ts_unreachable_code`), dockerfmt
  (`format_dockerfile`), screenshot (`screenshot`), etc. are opt-in extras; the
  matching hooks require them.
- **Consequences:** Light default install; a hook fails clearly if its extra is missing.

## ADR-006 — ruff pinned to py313 target despite 3.14 runtime
- **Status:** Accepted, temporary (FACT — `[tool.ruff]` comment)
- **Decision:** Keep ruff `target-version`/behaviour at py313 because `ruff format
  <=0.15.15` strips multi-except parentheses under py314.
- **Consequences:** Revisit when fixed upstream; `ruff==0.16.3` pinned and kept in sync
  with downstream `ruff-pre-commit` rev.

## ADR-007 — Coverage gate at 85%, quality gate with baseline
- **Status:** Accepted (FACT)
- **Decision:** `--cov-fail-under=85`; `scripts/quality_gate.py` + `regression_gate.py`
  record and verify a baseline (`.quality-gate-baseline.json`); SonarCloud gate on top.

## ADR-008 — README hooks table & context files are generated, not hand-written
- **Status:** Accepted (FACT — chrysa ADR D-0012 referenced in generated file headers)
- **Decision:** `tools/update_readme.py` regenerates the README TOC/table from the
  manifest; `scripts/gen_context_files.py` generates `handover.md` / `ai-instructions.md`.
- **Consequences:** Do not hand-edit generated sections; regenerate via make targets.

## ADR-009 — chrysa standards vendored into the repo
- **Status:** Accepted (FACT)
- **Decision:** `standards/rules/*.md` + `standards/STANDARDS.chrysa.md` are synced in
  (many `chore: sync ... standards` commits) so the repo is self-describing for agents.

## Referenced external ADRs (not restated)
- **D-0012** — generated context files (`handover.md`, `ai-instructions.md`).
- ADR gate itself is a hook (`adr_gate.py`) enforcing the chrysa ADR format in consumers.

## UNKNOWN
- Original dates/authors of the decisions above — not recorded in-repo as dated ADRs.
