#!/usr/bin/python3
"""Hook to detect Dockerfiles missing a HEALTHCHECK instruction."""

from __future__ import annotations

import re
from collections.abc import Sequence

_DISABLE_COMMENT = '# dockerfile-healthcheck: disable'
_FROM_RE = re.compile(r'^\s*FROM\s+', re.IGNORECASE)
_HEALTHCHECK_RE = re.compile(r'^\s*HEALTHCHECK\s+', re.IGNORECASE)

Violation = tuple[str, int, str]


def detect_missing_healthcheck(source: str, filename: str) -> list[Violation]:
    """Return a violation when the Dockerfile's final stage has no HEALTHCHECK."""
    if _DISABLE_COMMENT in source:
        return []

    lines = source.splitlines()
    last_from_lineno: int | None = None
    for idx, line in enumerate(lines):
        if line.strip().startswith('#'):
            continue
        if _FROM_RE.match(line):
            last_from_lineno = idx

    if last_from_lineno is None:
        return []

    for line in lines[last_from_lineno:]:
        if line.strip().startswith('#'):
            continue
        if _HEALTHCHECK_RE.match(line):
            return []

    return [
        (
            filename,
            last_from_lineno + 1,
            'Dockerfile final stage is missing a HEALTHCHECK instruction',
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Detect Dockerfiles missing HEALTHCHECK and return 1 if any found."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect Dockerfiles missing HEALTHCHECK instruction',
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
        for fname, lineno, msg in detect_missing_healthcheck(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
