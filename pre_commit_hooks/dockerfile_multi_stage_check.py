#!/usr/bin/python3
"""Hook to detect Dockerfiles that are missing a multi-stage build pattern."""

from __future__ import annotations

import re
from collections.abc import Sequence

_DISABLE_COMMENT = '# dockerfile-multi-stage-check: disable'
_FROM_RE = re.compile(r'^\s*FROM\s+\S+', re.IGNORECASE)
_STAGE_RE = re.compile(r'^\s*FROM\s+\S+\s+AS\s+(?P<name>\S+)', re.IGNORECASE)

Violation = tuple[str, int, str]


def _stage_names(source: str) -> set[str]:
    """Return the set of named build stages (``FROM … AS <name>``), lowercased."""
    names: set[str] = set()
    for line in source.splitlines():
        if line.strip().startswith('#'):
            continue
        match = _STAGE_RE.match(line)
        if match:
            names.add(match.group('name').lower())
    return names


def detect_missing_multi_stage(
    source: str,
    filename: str,
    require_targets: Sequence[str] | None = None,
) -> list[Violation]:
    """Return violations for missing multi-stage builds or required named targets.

    Every FROM counts as a stage, including a final ``FROM scratch`` — a build
    that copies artefacts into ``scratch`` is still a valid multi-stage build.

    When ``require_targets`` is given (e.g. ``("production", "dev")``), the
    Dockerfile must additionally declare a ``FROM … AS <target>`` stage for each
    name (case-insensitive); a missing one is its own violation. This enforces the
    shared-standards rule that application Dockerfiles ship both a ``production``
    and a ``dev`` stage.
    """
    if _DISABLE_COMMENT in source:
        return []

    from_count = 0
    for line in source.splitlines():
        if line.strip().startswith('#'):
            continue
        if _FROM_RE.match(line):
            from_count += 1

    violations: list[Violation] = []
    if from_count < 2:
        violations.append(
            (
                filename,
                1,
                f'Dockerfile has only {from_count} FROM stage(s); multi-stage builds required '
                '(deps → builder → production)',
            ),
        )
        return violations

    if require_targets:
        present = _stage_names(source)
        for target in require_targets:
            if target.lower() not in present:
                violations.append(
                    (
                        filename,
                        1,
                        f"Dockerfile is missing the required '{target}' build stage "
                        f'(FROM … AS {target}); a production and a dev stage are mandatory',
                    ),
                )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect Dockerfiles missing multi-stage builds and return 1 if any found."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect Dockerfiles missing multi-stage build pattern',
    )
    parser.add_argument('filenames', nargs='*')
    parser.add_argument(
        '--require-target',
        action='append',
        default=None,
        metavar='NAME',
        help='Require a named build stage (FROM … AS NAME). Repeatable, e.g. '
        '--require-target production --require-target dev.',
    )
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_missing_multi_stage(source, filename, args.require_target):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
