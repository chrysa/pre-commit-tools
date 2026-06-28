#!/usr/bin/python3
"""Hook to detect insecure set_cookie() calls missing secure/httponly/samesite (RGPD/ePrivacy)."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_SET_COOKIE = re.compile(r'\.set_cookie\s*\(')
_SECURE = re.compile(r'secure\s*=\s*True')
_HTTPONLY = re.compile(r'httponly\s*=\s*True')
_SAMESITE = re.compile(r'samesite\s*=')


def _call_region(text: str, paren_index: int) -> str:
    depth = 0
    for i in range(paren_index, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[paren_index : i + 1]
    return text[paren_index:]


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any set_cookie() call misses secure/httponly/samesite."""
    parser = argparse.ArgumentParser(description='Detect insecure set_cookie calls.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        text = Path(filename).read_text(encoding='utf-8')
        for match in _SET_COOKIE.finditer(text):
            line_start = text.rfind('\n', 0, match.start()) + 1
            line_end = text.find('\n', match.start())
            line = text[line_start : line_end if line_end != -1 else len(text)]
            if 'cookie-insecure: disable' in line:
                continue
            region = _call_region(text, match.end() - 1)
            if not (_SECURE.search(region) and _HTTPONLY.search(region) and _SAMESITE.search(region)):
                lineno = text.count('\n', 0, match.start()) + 1
                msg = f'[{filename}:{lineno}] set_cookie must set secure=True, httponly=True, samesite'
                print(msg)  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
