#!/usr/bin/python3
"""Hook to detect forbidden standalone tool config files (use [tool.*] in pyproject.toml)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

_FORBIDDEN = {'ruff.toml', 'mypy.ini', '.mypy.ini', 'pytest.ini', '.coveragerc'}


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any staged file is a forbidden standalone tool config file."""
    parser = argparse.ArgumentParser(description='Detect forbidden standalone tool config files.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        if Path(filename).name in _FORBIDDEN:
            msg = f'[{filename}] forbidden: move tool config into [tool.*] of pyproject.toml'
            print(msg)  # print-detection: disable
            ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
