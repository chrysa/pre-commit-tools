# Security — pre-commit-tools

Docs-only assessment. Tags: **FACT**, **INFERENCE**, **UNKNOWN**. No code was
changed. Any HIGH/CRITICAL finding is flagged for the owner to fix, not fixed here.

## Threat surface (INFERENCE)

This is a lint-tool library, not a running service: no network listener, no auth,
no database. It executes as pre-commit hooks over local files and in CI. The
realistic risks are (a) supply-chain (what it pulls in), (b) code execution when a
hook shells out or parses untrusted input, and (c) secrets accidentally committed
into the repo itself (fixtures/baselines).

## Secret scan of the repo (FACT)

- **No plaintext secret was surfaced** during this documentation pass. The repo
  ships secret-scanning infrastructure: `.gitleaks.toml`, `.secrets.baseline`
  (detect-secrets), `secret-scan.yml` workflow, and a local
  `.claude/hooks/secret-scanner.cjs`.
- `.secrets.baseline` and test fixtures intentionally contain **password-shaped
  strings** (ruff `S105/S106/S107` ignored in tests) — these are test data, not live
  credentials. INFERENCE: treat as non-secret; owner should confirm none is a real
  token. Location/nature only, values not reproduced here.

## Security-relevant hooks shipped (FACT)

The project *provides* defensive hooks (its product):
`django_hardcoded_secret`, `ts_hardcoded_secret`, `cors_allow_all`,
`django_cookie_security`, `fastapi_cookie_insecure`, `pii_hardcoded`, `pii_in_logs`,
`sentry_no_default_pii`, `react_token_localstorage`. These enforce security norms in
*consumer* repos.

## Supply chain (FACT / flag)

- **FLAG-SEC-001 (INFERENCE, MEDIUM)** — `dev`/quality-gate extra installs
  `chrysa-quality-gate` via **`git+ssh` from a mutable ref**
  (`chrysa-lib.git@v0.3.1#subdirectory=...`). A tag is used (good), but git deps
  bypass PyPI hash pinning. Owner decision: acceptable for a private internal tool;
  document that consumers installing only the runtime hooks do **not** pull this.
- **FACT** — Runtime parsing deps `tree-sitter` + `tree-sitter-typescript` are version-
  ranged; `ruff` is pinned. Dependabot + `dependabot_classified_deps` hook govern bumps.
- **FACT** — `.mcp.json` is present at repo root; MCP server definitions were not
  audited here (UNKNOWN whether any embed tokens — quick read advised by owner).

## Code-execution considerations (INFERENCE)

- Several hooks shell out to external tools (`helm_lint` → helm, `format_dockerfile`,
  `js_syntax_check`, screenshot capture → `requests`/browser). Ruff `S404/S603/S607`
  are relevant; the repo ignores `S603/S607` (partial-path process start) by policy.
  INFERENCE (LOW): inputs are developer-controlled files, so injection risk is low,
  but owner should confirm no hook passes untrusted content to a shell string.

## HIGH/CRITICAL findings

- **None identified** in this documentation pass.

## Owner action items (non-blocking)

1. Confirm `.secrets.baseline` / fixtures hold only synthetic credentials.
2. Confirm `.mcp.json` embeds no tokens (env-referenced only).
3. Decide whether the `git+ssh` quality-gate dep should be vendored/pinned by hash.
