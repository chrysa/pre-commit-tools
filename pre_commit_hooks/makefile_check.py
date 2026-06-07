#!/usr/bin/python3
"""Hook to enforce the chrysa archetype-tiered Makefile contract.

See chrysa/shared-standards EXECUTION_STANDARD.md §1 for the contract this enforces.

Each Makefile must declare its tier on a marker line::

    # makefile-tier: lib        # one of: lib | python-app | fullstack | infra

The hook then checks, for the declared tier:
  * all required targets are present,
  * no forbidden target name is used (fmt / type-check / tests),
  * no legacy ``docker-compose <cmd>`` invocation (must be ``docker compose``),
  * no glued ``docker compose`` typo (``docker composelogs``),
  * a ``help`` target and a ``.PHONY`` declaration exist,
  * every directory a lint/test/format rule references actually exists.

Warnings (non-fatal) are emitted for targets missing from ``.PHONY`` and for a
Makefile with no ``## `` self-documenting comments.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VALID_TIERS = ('lib', 'python-app', 'fullstack', 'infra')

# Required targets per tier (see EXECUTION_STANDARD.md §1.2 / §1.3). These must
# be definable correctly with no extra infrastructure, so they are mandatory.
_CORE = {'help', 'install', 'lint', 'format', 'test', 'build', 'clean', 'pre-commit'}
_LIB = _CORE | {'dev', 'typecheck', 'test-cov'}
_APP = _LIB | {'docker-up', 'docker-down', 'ci'}
_FULLSTACK = _APP
_INFRA = _CORE | {'dev'}

REQUIRED_BY_TIER: dict[str, set[str]] = {
    'lib': _LIB,
    'python-app': _APP,
    'fullstack': _FULLSTACK,
    'infra': _INFRA,
}

# Recommended targets per tier (§1.5). These depend on supporting infrastructure
# (a Dockerfile.test, scripts/quality_gate.py, a wired frontend build), so their
# absence is a warning, not an error — adopt them as the infra lands.
_REC_LIB = {'docker-test'}
_REC_APP = _REC_LIB | {'quality-gate-baseline', 'quality-gate-verify'}
_REC_FULLSTACK = _REC_APP | {'web-build', 'web-lint', 'web-typecheck', 'e2e'}

RECOMMENDED_BY_TIER: dict[str, set[str]] = {
    'lib': _REC_LIB,
    'python-app': _REC_APP,
    'fullstack': _REC_FULLSTACK,
    'infra': set(),
}

# Forbidden target name -> canonical replacement (§1.4).
FORBIDDEN_TARGETS = {'fmt': 'format', 'type-check': 'typecheck', 'tests': 'test'}

# Tools whose first positional path argument(s) must point at real directories.
PATH_TOOLS = {'ruff', 'mypy', 'pytest', 'black', 'isort', 'flake8', 'pylint'}
# Sub-commands / flags that follow a tool but are not path arguments.
_TOOL_SKIP = {'check', 'format', 'run', 'format-check', 'lint'}

_TIER_RE = re.compile(r'^#\s*makefile-tier:\s*([A-Za-z][\w-]*)', re.MULTILINE)
_TARGET_RE = re.compile(r'^([A-Za-z0-9_][\w.-]*)\s*:(?!=)')
_VAR_RE = re.compile(r'^([A-Za-z_][\w]*)\s*[:?]?=\s*(.*?)\s*$')
_LEGACY_DC_RE = re.compile(
    r'docker-compose\s+(up|down|build|run|logs|ps|exec|config|restart|stop|start|pull|--)',
)
_GLUED_DC_RE = re.compile(r'docker\s+compose[a-z]')
_INCLUDE_RE = re.compile(r'^[ \t]*-?include[ \t]+(.+?)[ \t]*$', re.MULTILINE)
_FIND_NAME_RE = re.compile(r'find\s+(\S+).*?-name\s+["\']?([^"\'\s]+)')


def _included_files(text: str, root: Path) -> list[Path]:
    """Resolve `include` directives to a best-effort list of existing files.

    Many chrysa Makefiles split targets across `makefiles/*.makefile` pulled in
    via `include $(shell find ... -name "*.makefile")`. The checker must read
    those too, or it reports required targets as missing when they are simply
    defined in an included fragment.
    """
    files: list[Path] = []
    for match in _INCLUDE_RE.finditer(text):
        spec = match.group(1)
        find_specs = _FIND_NAME_RE.findall(spec)
        if find_specs:
            for directory, pattern in find_specs:
                base = root / directory
                if base.is_dir():
                    files.extend(sorted(base.rglob(pattern)))
            continue
        wildcard = re.search(r'\$\(wildcard\s+([^)]+)\)', spec)
        if wildcard:
            for token in wildcard.group(1).split():
                files.extend(f for f in sorted(root.glob(token)) if f.is_file())
            continue
        if '$(' in spec or '${' in spec:
            continue  # unresolvable variable reference
        for token in spec.split():
            files.extend(f for f in sorted(root.glob(token)) if f.is_file())
    return files


def _find_marker_tier(text: str) -> str | None:
    match = _TIER_RE.search(text)
    return match.group(1) if match else None


def _collect_targets(lines: list[str]) -> set[str]:
    """Return explicit, non-pattern, non-special target names."""
    targets: set[str] = set()
    for line in lines:
        if line.startswith('\t') or line.startswith('.') or '%' in line.split(':', 1)[0]:
            continue
        match = _TARGET_RE.match(line)
        if match:
            targets.add(match.group(1))
    return targets


def _collect_vars(lines: list[str]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for line in lines:
        if line.startswith('\t'):
            continue
        match = _VAR_RE.match(line)
        if match:
            variables[match.group(1)] = match.group(2)
    return variables


def _collect_phony(lines: list[str]) -> set[str] | None:
    """Return the union of all .PHONY target names, or None if no .PHONY line."""
    phony: set[str] = set()
    found = False
    collecting = False
    for raw in lines:
        line = raw.rstrip('\n')
        if line.startswith('.PHONY:'):
            found = True
            collecting = True
            line = line[len('.PHONY:') :]
        elif not collecting:
            continue
        cont = line.endswith('\\')
        phony.update(tok for tok in line.rstrip('\\').split() if tok)
        collecting = cont
    return phony if found else None


def _expand(token: str, variables: dict[str, str]) -> str:
    """Expand $(VAR)/${VAR} one level using collected variables."""

    def repl(match: re.Match[str]) -> str:
        return variables.get(match.group(1), match.group(0))

    return re.sub(r'\$[({](\w+)[)}]', repl, token)


def _strip_quotes(text: str) -> str:
    """Replace quoted spans with a space so their contents are ignored."""
    return re.sub(r'"[^"]*"|\'[^\']*\'', ' ', text)


def _candidate_paths(recipe: str, variables: dict[str, str]) -> list[str]:
    """Extract host path arguments for path-checking tools invoked directly.

    Only tools run *directly on the host* are checked: the tool must be the
    command being executed (first token of a shell command), never an argument.
    This deliberately ignores tools inside ``docker exec`` / ``docker compose
    run`` (their paths are container-side) and package lists like
    ``pip install pytest-cov`` (those are package names, not paths).
    """
    paths: list[str] = []
    # Drop quoted spans, then any trailing shell ``#`` comment.
    cleaned = _strip_quotes(recipe).split('#', 1)[0]
    for command in re.split(r'&&|\|\||;|\|', cleaned):
        tokens = command.split()
        if not tokens or tokens[0].lstrip('@-') not in PATH_TOOLS:
            continue
        for token in tokens[1:]:
            if token.startswith('-'):
                break  # positional path args precede flags; stop at first flag
            if '=' in token or token in _TOOL_SKIP:
                continue
            expanded = _expand(token, variables)
            if '$' in expanded or any(ch in expanded for ch in '*?<>|"\''):
                continue
            if re.fullmatch(r'[A-Za-z0-9_][\w./-]*', expanded):
                paths.append(expanded.rstrip('/'))
    return paths


def _check_structure(
    text: str,
    lines: list[str],
    targets: set[str],
) -> tuple[list[str], list[str]]:
    """Check tier marker, required/forbidden targets, help, .PHONY, ## comments."""
    errors: list[str] = []
    warnings: list[str] = []

    tier = _find_marker_tier(text)
    if tier is None:
        errors.append(
            f"missing '# makefile-tier:' marker (expected one of: {', '.join(VALID_TIERS)})",
        )
    elif tier not in VALID_TIERS:
        errors.append(f"invalid tier '{tier}' (expected one of: {', '.join(VALID_TIERS)})")

    if tier in REQUIRED_BY_TIER:
        missing = sorted(REQUIRED_BY_TIER[tier] - targets)
        if missing:
            errors.append(f"tier '{tier}' is missing required targets: {', '.join(missing)}")

    if tier in RECOMMENDED_BY_TIER:
        missing_rec = sorted(RECOMMENDED_BY_TIER[tier] - targets)
        if missing_rec:
            warnings.append(
                f"tier '{tier}' is missing recommended targets: {', '.join(missing_rec)}",
            )

    errors.extend(
        f"forbidden target '{bad}' — rename to '{good}'" for bad, good in FORBIDDEN_TARGETS.items() if bad in targets
    )

    if 'help' not in targets:
        errors.append("missing 'help' target")

    phony = _collect_phony(lines)
    if phony is None:
        errors.append('no .PHONY declaration found')
    # A shell-computed .PHONY (e.g. `.PHONY: $(shell grep ... )`) lists every
    # target dynamically; we cannot resolve it statically, so trust it.
    elif not any(line.startswith('.PHONY:') and 'shell' in line for line in lines):
        not_phony = sorted(targets - phony - {'help'})
        if not_phony:
            warnings.append(f'.PHONY does not list: {", ".join(not_phony)}')

    if '## ' not in text:
        warnings.append("no '## ' self-documenting comments found (help will be empty)")

    return errors, warnings


def _check_recipes(lines: list[str], repo_root: Path) -> list[str]:
    """Check recipe lines for legacy/typo'd docker-compose and missing paths."""
    errors: list[str] = []
    variables = _collect_vars(lines)
    for raw in lines:
        if not raw.startswith('\t'):
            continue
        recipe = raw.strip()
        if recipe.startswith('#'):
            continue
        # Strip quoted spans so e.g. echo "docker-compose config OK" is ignored.
        unquoted = _strip_quotes(recipe)
        if _LEGACY_DC_RE.search(unquoted):
            errors.append(f"legacy 'docker-compose' CLI (use 'docker compose'): {recipe}")
        if _GLUED_DC_RE.search(unquoted):
            errors.append(f"glued 'docker compose' typo: {recipe}")
        errors.extend(
            f"rule references missing path '{candidate}': {recipe}"
            for candidate in _candidate_paths(recipe, variables)
            if not (repo_root / candidate).exists()
        )
    return errors


def check_makefile(path: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one Makefile."""
    text = path.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()
    targets = _collect_targets(lines)
    # Targets may be defined in included fragments — fold them in so required
    # targets are not reported missing when an `include`d file provides them.
    for included in _included_files(text, path.parent):
        try:
            targets |= _collect_targets(included.read_text(encoding='utf-8', errors='replace').splitlines())
        except OSError:
            continue

    errors, warnings = _check_structure(text, lines, targets)
    errors.extend(_check_recipes(lines, path.parent))
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    """Check every Makefile passed (or ./Makefile when none given)."""
    parser = argparse.ArgumentParser(description='Enforce the chrysa Makefile contract')
    parser.add_argument('filenames', nargs='*', help='Makefile paths (default: ./Makefile)')
    args = parser.parse_args(argv)

    paths = [Path(name) for name in args.filenames] or [Path('Makefile')]
    retval = 0
    for path in paths:
        if path.name != 'Makefile' or not path.exists():
            continue
        errors, warnings = check_makefile(path)
        for warning in warnings:
            print(f'{path}: warning: {warning}', file=sys.stderr)
        for error in errors:
            print(f'{path}: error: {error}', file=sys.stderr)
        if errors:
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
