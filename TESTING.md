# Testing — pre-commit-tools

Tags: **FACT** (verified against config/files), **INFERENCE**, **UNKNOWN**.
Commands below were read from `Makefile`, `pyproject.toml`, `Dockerfile.test`, and
`.github/workflows/`. They were **not executed** as part of writing this doc (the
chrysa host gotcha `-p no:query_optimizer` / `--no-cov` may apply if run locally
outside the container).

## Test layout (FACT)

- One test module per hook: `tests/test_<slug>.py` — **81 files** (`tests/test_*.py`).
- Shared conventions (CLAUDE.md, FACT):
  - `_write(tmp_path, name, content)` helper to create temp files.
  - Single-line content with explicit `\n`, not triple-quoted blocks.
  - Grouping classes `TestMyFunction` + `TestMyHookMain`.
  - `@pytest.mark.parametrize` for multiple inputs.
- Test config (FACT, `pyproject.toml`): `addopts = "-v --tb=short --cov-fail-under=85"`;
  `S101` (assert) and `PLR2004` (magic values) are ignored in tests.

## Commands (FACT — from Makefile)

```bash
make test            # pytest (all)
make test-cov        # pytest with coverage report
make test-fail-fast  # pytest -x (stop on first failure)
make test-debug      # pytest --pdb on first failure
make docker-test     # run the suite inside the CI-matching container
make quality         # ruff lint + ruff format-check + mypy
make ci              # lint + typecheck + test
```

Convention (FACT, CLAUDE.md): run tests via `make`, not by calling `pytest`
directly on the host.

### Container run (FACT — `Dockerfile.test`)

```bash
docker build -f Dockerfile.test -t pre-commit-tools-test .
docker run --rm pre-commit-tools-test
# CMD: pytest --cov=pre_commit_hooks --cov-branch \
#      --cov-report=xml:reports/coverage.xml --cov-report=term-missing
```
The image installs the `test,yaml,ts_unreachable_code,format_dockerfile,dead_code,screenshot`
extras and `git` (needed by hooks that inspect the working tree, e.g. adr-gate,
dockerfile multi-stage check).

## Coverage gate (FACT)

- Global gate: **>= 85%** (`--cov-fail-under=85`).
- Branch coverage enabled in the container run (`--cov-branch`).
- Reported to SonarCloud (`sonar-project.properties`, `SONAR_TOKEN` secret; `.coverage`
  and `.quality-gate-*.json` present in tree).

## CI (FACT — `.github/workflows/`)

- `ci.yml`: jobs cover **version**, **lint** (reusable `lint-python.yml`), **test**,
  **sonar** (`sonar-scan-python@v1.10.0`). Python **3.14 only** (artifact
  `test-results-3.14`, `python-version: "3.14"`).
- `pre-commit.yml`: runs `pre-commit/action` and MUST `pip install -e .` first.
- `mutation-testing.yml`: mutation-testing job present (tool/scope UNKNOWN — not read).
- `quality-gate-check.yml`, `secret-scan.yml`, `sonar.yml`: additional gates.

## Regression / quality gate (FACT)

```bash
make quality-gate-baseline   # record baseline metrics
make quality-gate-verify     # fail if regressed since baseline
```
Baselines stored in `.quality-gate-baseline.json`; `scripts/quality_gate.py` and
`regression_gate.py` implement the logic.

## Gaps / UNKNOWNs

- Actual current coverage % and pass/fail state at HEAD: UNKNOWN (not executed here).
- Mutation-testing configuration and thresholds: UNKNOWN (workflow body not read).
- Whether the host venv can run `pytest` without the `-p no:query_optimizer` /
  `--no-cov` chrysa gotcha: UNKNOWN — prefer `make docker-test`.
