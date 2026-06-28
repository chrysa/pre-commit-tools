#!/usr/bin/python3
"""Hook to detect forbidden setup.py / packaging setup.cfg files (use pyproject.toml)."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

_PACKAGING_SECTION = re.compile(r'^\s*\[(metadata|options)\]', re.MULTILINE)


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 for any setup.py or any packaging setup.cfg."""
    parser = argparse.ArgumentParser(description='Detect forbidden setup packaging files.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        name = Path(filename).name
        if name == 'setup.py':
            msg = f'[{filename}] forbidden: use pyproject.toml for packaging'
            print(msg)  # print-detection: disable
            ret = 1
        elif name == 'setup.cfg':
            content = Path(filename).read_text(encoding='utf-8')
            if _PACKAGING_SECTION.search(content):
                msg = f'[{filename}] forbidden: setup.cfg packaging — use pyproject.toml'
                print(msg)  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
