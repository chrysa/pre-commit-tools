# Documentation review — pre-commit-tools

Docs-only pass (no source changed). Records what exists, what was added, what was
skipped, and the contradictions found.

## Existing docs (preserved)

- `README.md` — full per-hook reference + usage (auto-generated TOC/table). Authoritative for hook catalogue.
- `CLAUDE.md` — agent operating guide (commands, conventions, pitfalls, GitNexus, standards core).
- `ARCHITECTURE.md` — stack, layout, entrypoints, build/test commands.
- `AGENTS.md`, `CONTRIBUTING.md`, `CHANGELOG.md` (git-cliff generated), `LICENSE`.
- `handover.md`, `ai-instructions.md`, `llms-full.txt`, `context-map.json` — GENERATED (ADR D-0012); do not hand-edit.
- `standards/` — vendored chrysa standards; `docs/reference/github-inspiration.md`.

## Docs added this pass

- `REQUIREMENTS.md` — REQ-* matrix (functional + NFR), reverse-engineered.
- `CONSTRAINTS.md` — CON-* tagged constraints (platform, toolchain, conventions, supply chain, process).
- `DECISIONS.md` — reverse-engineered ADR log (ADR-001..009 + referenced external ADRs).
- `TESTING.md` — verified test/CI/coverage commands (commands read, not executed).
- `SECURITY.md` — threat-surface + secret-scan assessment + owner action items.
- `GLOSSARY.md` — repo vocabulary.
- `REVIEW.md` — this file.

## Docs skipped (with reason)

- **PRD** — no product/user-facing surface; it is a dev tool library. README already states purpose. Skipped.
- **TRD** — ARCHITECTURE.md already covers the technical design; a separate TRD would duplicate. Skipped.
- **OBSERVABILITY** — no runtime service, no logs/metrics/traces to operate. `tools/logger.py` is build-time only. Skipped (not applicable).
- **ROADMAP** — no committed roadmap artefact in-repo; inventing one would violate the no-fabrication rule. Skipped (record: none found).

## Contradictions found (for owner)

1. **Python version matrix.** CLAUDE.md ("Matrix: Python 3.12, 3.13, 3.14") and
   README badge history imply a 3.12–3.14 matrix, but `pyproject.toml`
   (`requires-python = ">=3.14"`), `Dockerfile.test` (`python:3.14-slim`), and
   `ci.yml`/`publish.yml` (`python-version: "3.14"`, artifact `test-results-3.14`)
   target **3.14 only**. → CLAUDE.md matrix claim is stale. (CON-022, ADR-003)
2. **Entry-point location.** CLAUDE.md and the "Creating a new hook" checklist say
   entry points and deps live in **`setup.cfg`**, and the Architecture block lists
   `setup.cfg`. The real source of truth is **`pyproject.toml`**
   (`[project.scripts]`, `[project.optional-dependencies]`); no `setup.cfg` drives
   this. → CLAUDE.md references are stale. (ADR-004)
3. **Version drift in prose.** ARCHITECTURE.md says "package version `0.0.34`" and
   "~80 hooks / 81 hook ids"; the manifest and `[project.scripts]` now hold **82**
   ids each. Minor count drift — verify the current version in `pyproject.toml`
   before quoting.

## Doc debt / recommendations (non-blocking)

- Fix the three contradictions above in CLAUDE.md / ARCHITECTURE.md (owner; source edit out of scope here).
- Consider regenerating the README hook count and ARCHITECTURE counts (82) via `make`.
- `.mcp.json` and `.claude/ape/` not deeply audited — quick owner review suggested.

## Method / integrity

Every claim is tagged FACT / INFERENCE / UNKNOWN in the target docs. Commands in
TESTING.md were read from config, not executed. No secrets copied. No source, test,
dependency, CI, or config file was modified.
