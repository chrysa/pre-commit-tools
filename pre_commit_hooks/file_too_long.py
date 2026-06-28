#!/usr/bin/python3
"""Hook to detect Python files exceeding the maximum line count (default 500)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any staged file exceeds --max-lines lines."""
    parser = argparse.ArgumentParser(description='Detect over-long files.')
    parser.add_argument('--max-lines', type=int, default=500)
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        count = len(Path(filename).read_text(encoding='utf-8').splitlines())
        if count > args.max_lines:
            msg = f'[{filename}] {count} lines exceeds max {args.max_lines}'
            print(msg)  # print-detection: disable
            ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
