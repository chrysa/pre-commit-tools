#!/usr/bin/python3
"""Hook to detect `FROM image:latest` in Dockerfiles."""

from __future__ import annotations

import re
from collections.abc import Sequence

_DISABLE_COMMENT = '# dockerfile-no-latest: disable'
_FROM_LATEST_RE = re.compile(r'^\s*FROM\s+\S+:latest(\s|$)', re.IGNORECASE)
_FROM_SCRATCH_RE = re.compile(r'^\s*FROM\s+scratch(\s|$)', re.IGNORECASE)

Violation = tuple[str, int, str]


def detect_from_latest(source: str, filename: str) -> list[Violation]:
    """Detect FROM image:latest instructions in Dockerfile source."""
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _DISABLE_COMMENT in line:
            continue
        if _FROM_SCRATCH_RE.match(line):
            continue
        m = _FROM_LATEST_RE.match(line)
        if m:
            violations.append(
                (filename, lineno, 'FROM with :latest tag is not reproducible'),
            )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect FROM :latest tags in Dockerfiles and return 1 if any are found."""
    import argparse

    parser = argparse.ArgumentParser(description='Detect FROM :latest in Dockerfiles')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_from_latest(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
