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

# Required targets per tier (see EXECUTION_STANDARD.md §1.2 / §1.3).
_CORE = {'help', 'install', 'lint', 'format', 'test', 'build', 'clean', 'pre-commit'}
_LIB = _CORE | {'dev', 'typecheck', 'test-cov', 'docker-test'}
_APP = _LIB | {
    'docker-up',
    'docker-down',
    'quality-gate-baseline',
    'quality-gate-verify',
    'ci',
}
_FULLSTACK = _APP | {'web-build', 'web-lint', 'web-typecheck', 'e2e'}
_INFRA = _CORE | {'dev'}

REQUIRED_BY_TIER: dict[str, set[str]] = {
    'lib': _LIB,
    'python-app': _APP,
    'fullstack': _FULLSTACK,
    'infra': _INFRA,
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


def _candidate_paths(recipe: str, variables: dict[str, str]) -> list[str]:
    """Extract path arguments passed to a path-checking tool on a recipe line."""
    paths: list[str] = []
    # Only inspect up to the first shell separator so we stay on one command.
    segment = re.split(r'&&|\|\||;', recipe, maxsplit=1)[0]
    # Drop quoted spans so tool names inside echo strings are not mistaken
    # for real invocations (e.g. @echo "Run mypy type checking").
    segment = re.sub(r'"[^"]*"|\'[^\']*\'', ' ', segment)
    tokens = segment.split()
    capturing = False
    for token in tokens:
        bare = token.lstrip('@-')
        if bare in PATH_TOOLS:
            capturing = True
            continue
        if not capturing:
            continue
        if token.startswith('-') or '=' in token or token in _TOOL_SKIP:
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

    errors.extend(
        f"forbidden target '{bad}' — rename to '{good}'" for bad, good in FORBIDDEN_TARGETS.items() if bad in targets
    )

    if 'help' not in targets:
        errors.append("missing 'help' target")

    phony = _collect_phony(lines)
    if phony is None:
        errors.append('no .PHONY declaration found')
    else:
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
        if _LEGACY_DC_RE.search(recipe):
            errors.append(f"legacy 'docker-compose' CLI (use 'docker compose'): {recipe}")
        if _GLUED_DC_RE.search(recipe):
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
