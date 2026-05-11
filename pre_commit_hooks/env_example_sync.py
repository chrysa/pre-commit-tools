#!/usr/bin/python3
"""Hook to check that .env and .env.example files are in sync (same keys)."""

from __future__ import annotations

import argparse
import os
import re
from collections.abc import Sequence
from pathlib import Path

_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=', re.MULTILINE)
_COMMENT_RE = re.compile(r'^\s*#')


def _parse_keys(path: Path) -> set[str]:
    """Extract all KEY names from an env file, ignoring comments and blank lines."""
    keys: set[str] = set()
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or _COMMENT_RE.match(line):
                    continue
                m = _KEY_RE.match(line)
                if m:
                    keys.add(m.group(1))
    except (OSError, UnicodeDecodeError):
        pass
    return keys


def check_env_sync(env_path: Path, example_path: Path) -> list[str]:
    """Return list of error messages if .env and .env.example are out of sync."""
    errors: list[str] = []
    if not env_path.exists():
        return errors
    if not example_path.exists():
        errors.append(f'{example_path}: missing — create it from {env_path}')
        return errors

    env_keys = _parse_keys(env_path)
    example_keys = _parse_keys(example_path)

    only_in_env = env_keys - example_keys
    only_in_example = example_keys - env_keys

    for key in sorted(only_in_env):
        errors.append(
            f'{env_path}: key {key!r} present in .env but missing from .env.example',
        )
    for key in sorted(only_in_example):
        errors.append(
            f'{example_path}: key {key!r} present in .env.example but missing from .env',
        )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    """Check .env / .env.example synchronisation and return 1 if out of sync."""
    parser = argparse.ArgumentParser(
        description='Check that .env and .env.example have the same keys',
    )
    parser.add_argument(
        'filenames',
        nargs='*',
        help='.env or .env.example files to check',
    )
    parser.add_argument(
        '--env-file',
        default='.env',
        help='Path to the .env file (default: .env)',
    )
    parser.add_argument(
        '--example-file',
        default='.env.example',
        help='Path to the .env.example file (default: .env.example)',
    )
    args = parser.parse_args(argv)

    # Collect directories to check from the filenames passed
    if args.filenames:
        dirs: set[str] = set()
        for f in args.filenames:
            dirs.add(os.path.dirname(os.path.abspath(f)) if os.path.dirname(f) else '.')
    else:
        dirs = {'.'}

    retval = 0
    for directory in sorted(dirs):
        env_path = Path(directory) / args.env_file
        example_path = Path(directory) / args.example_file
        for msg in check_env_sync(env_path, example_path):
            print(msg)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
