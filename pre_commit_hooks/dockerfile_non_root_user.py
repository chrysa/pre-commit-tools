#!/usr/bin/python3
"""Hook to detect Dockerfiles where the final stage runs as root."""

from __future__ import annotations

import re
from collections.abc import Sequence

_DISABLE_COMMENT = '# dockerfile-non-root-user: disable'
_FROM_RE = re.compile(r'^\s*FROM\s+', re.IGNORECASE)
_USER_RE = re.compile(r'^\s*USER\s+(\S+)', re.IGNORECASE)
_ROOT_USER_RE = re.compile(r'^\s*USER\s+root\b', re.IGNORECASE)

Violation = tuple[str, int, str]


def detect_root_user(source: str, filename: str) -> list[Violation]:
    """Return a violation when the Dockerfile's final stage has no USER or uses USER root."""
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

    final_stage_lines = lines[last_from_lineno:]
    user_found = False

    for idx, line in enumerate(final_stage_lines):
        if line.strip().startswith('#'):
            continue
        if _ROOT_USER_RE.match(line):
            return [
                (
                    filename,
                    last_from_lineno + idx + 1,
                    'Dockerfile final stage uses USER root; switch to a non-root user',
                ),
            ]
        if _USER_RE.match(line):
            user_found = True

    if not user_found:
        return [
            (
                filename,
                last_from_lineno + 1,
                'Dockerfile final stage has no USER instruction; add a non-root user',
            ),
        ]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    """Detect Dockerfiles with missing or root USER in final stage; return 1 if found."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect Dockerfiles running as root in the final stage',
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
        for fname, lineno, msg in detect_root_user(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
