#!/usr/bin/python3
"""Hook to detect Dockerfiles that are missing a multi-stage build pattern."""

from __future__ import annotations

import re
from collections.abc import Sequence

_DISABLE_COMMENT = '# dockerfile-multi-stage-check: disable'
_FROM_RE = re.compile(r'^\s*FROM\s+\S+', re.IGNORECASE)
_FROM_SCRATCH_RE = re.compile(r'^\s*FROM\s+scratch(\s|$)', re.IGNORECASE)

Violation = tuple[str, int, str]


def detect_missing_multi_stage(source: str, filename: str) -> list[Violation]:
    """Return violations when the Dockerfile has only one non-scratch FROM stage."""
    if _DISABLE_COMMENT in source:
        return []

    from_count = 0
    for line in source.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            continue
        if _FROM_RE.match(line) and not _FROM_SCRATCH_RE.match(line):
            from_count += 1

    if from_count < 2:
        return [
            (
                filename,
                1,
                f'Dockerfile has only {from_count} FROM stage(s); multi-stage builds required '
                '(deps → builder → production)',
            ),
        ]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    """Detect Dockerfiles missing multi-stage builds and return 1 if any found."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect Dockerfiles missing multi-stage build pattern',
    )
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
        except OSError, UnicodeDecodeError:
            continue
        for fname, lineno, msg in detect_missing_multi_stage(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
