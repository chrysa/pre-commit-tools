#!/usr/bin/python3
"""Hook to enforce Django production cookie-security flags (RGPD/ePrivacy)."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_REQUIRED_TRUE = (
    'SESSION_COOKIE_HTTPONLY',
    'CSRF_COOKIE_HTTPONLY',
    'SESSION_COOKIE_SECURE',
    'CSRF_COOKIE_SECURE',
)
_REQUIRED_SET = (
    'SESSION_COOKIE_SAMESITE',
    'CSRF_COOKIE_SAMESITE',
)


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if a Django prod settings file misses a required cookie-security flag."""
    parser = argparse.ArgumentParser(description='Enforce Django cookie-security flags.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        content = Path(filename).read_text(encoding='utf-8')
        for flag in _REQUIRED_TRUE:
            if not re.search(rf'^\s*{flag}\s*=\s*True\b', content, re.MULTILINE):
                print(f'[{filename}] missing or non-True {flag} = True')  # print-detection: disable
                ret = 1
        for flag in _REQUIRED_SET:
            if not re.search(rf'^\s*{flag}\s*=', content, re.MULTILINE):
                print(f'[{filename}] missing {flag}')  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
