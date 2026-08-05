#!/usr/bin/python3
"""Hook to detect ``docker run`` invocations that mount the repo as root.

Enforces the shared-standards rule *Any container that bind-mounts a repo runs as
the host UID*: a throwaway container started without ``--user`` runs as root, and
anything it writes into the bind mount lands root-owned. Those artifacts are
unremovable without ``sudo`` and break the next run of the dev container with
``EACCES``. Measured on the fleet: 11 repositories, 25 191 root-owned files.

The check is static — it scans Makefiles and shell scripts for ``docker run``
followed by a host-path bind mount (``-v "$(PWD)":/x``, ``-v .:/x``, ``-v $PWD:/x``)
and flags the ones that never pass ``--user``/``-u``.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence

_DISABLE_COMMENT = '# docker-run-host-user: disable'

# A mount whose source is the repository (or a path inside it) rather than a
# named volume: `.`, `./frontend`, `$(PWD)`, `${PWD}`, `$PWD`, `$(CURDIR)`.
_REPO_SOURCE = re.compile(
    r"""-v\s+["']?(?:\.(?:/[^:"'\s]*)?|\$\((?:PWD|CURDIR)\)(?:/[^:"'\s]*)?"""
    r"""|\$\{?PWD\}?(?:/[^:"'\s]*)?)["']?:""",
)
_HAS_USER = re.compile(r'(?:^|\s)(?:--user(?:[=\s]|$)|-u\s)')
# `@` and `-` are Make recipe prefixes (silence / ignore-errors), so they may sit
# directly against the command.
_DOCKER_RUN = re.compile(r'(?:^|[\s;&|(@-])docker\s+run(?:\s|$)')

Violation = tuple[str, int, str]


def _logical_lines(source: str) -> list[tuple[int, str]]:
    """Join backslash-continued lines, keeping the line number of the first one."""
    out: list[tuple[int, str]] = []
    buf = ''
    start = 0
    for number, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.rstrip()
        if not buf:
            start = number
        if stripped.endswith('\\'):
            buf += stripped[:-1] + ' '
            continue
        out.append((start, buf + stripped))
        buf = ''
    if buf:
        out.append((start, buf))
    return out


def detect_root_repo_mounts(source: str, filename: str) -> list[Violation]:
    """Return one violation per ``docker run`` mounting the repo without ``--user``."""
    if _DISABLE_COMMENT in source:
        return []
    violations: list[Violation] = []
    for lineno, line in _logical_lines(source):
        if not _DOCKER_RUN.search(line):
            continue
        if not _REPO_SOURCE.search(line):
            continue
        if _HAS_USER.search(line):
            continue
        violations.append(
            (
                filename,
                lineno,
                'docker run bind-mounts the repository without --user: it writes '
                'root-owned files into the tree. Add '
                '--user $(shell id -u):$(shell id -g) (Makefile) or --user "$(id -u):$(id -g)" (shell).',
            )
        )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filenames', nargs='*', help='Filenames to check.')
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_root_repo_mounts(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
