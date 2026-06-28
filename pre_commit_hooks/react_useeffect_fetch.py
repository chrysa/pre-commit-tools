#!/usr/bin/python3
"""Hook to detect data fetching (fetch/axios) inside a React useEffect callback."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_USEEFFECT = re.compile(r'\buseEffect\s*\(')
_FETCH = re.compile(r'\bfetch\s*\(|\baxios\s*\.\s*(get|post|put|delete|patch|request)\s*\(')


def _effect_region(text: str, start: int) -> str:
    """Return the source spanning the balanced parentheses of the useEffect( at start."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any useEffect callback performs data fetching."""
    parser = argparse.ArgumentParser(description='Detect fetch/axios inside useEffect.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        text = Path(filename).read_text(encoding='utf-8')
        for match in _USEEFFECT.finditer(text):
            line_start = text.rfind('\n', 0, match.start()) + 1
            line_end = text.find('\n', match.start())
            line = text[line_start : line_end if line_end != -1 else len(text)]
            if 'react-useeffect-fetch: disable' in line:
                continue
            region = _effect_region(text, match.end() - 1)
            if _FETCH.search(region):
                lineno = text.count('\n', 0, match.start()) + 1
                msg = f'[{filename}:{lineno}] data fetching inside useEffect — use useQuery/useMutation'
                print(msg)  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
