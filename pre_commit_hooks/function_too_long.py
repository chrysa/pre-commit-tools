#!/usr/bin/python3
"""Hook to detect Python functions exceeding the maximum line count (default 50)."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Sequence
from pathlib import Path


def _disabled(source_lines: list[str], lineno: int) -> bool:
    idx = lineno - 1
    return 0 <= idx < len(source_lines) and 'function-too-long: disable' in source_lines[idx]


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any function exceeds --max-lines lines."""
    parser = argparse.ArgumentParser(description='Detect over-long functions.')
    parser.add_argument('--max-lines', type=int, default=50)
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        source = Path(filename).read_text(encoding='utf-8')
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        source_lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.end_lineno is not None:
                length = node.end_lineno - node.lineno + 1
                if length > args.max_lines and not _disabled(source_lines, node.lineno):
                    msg = f'[{filename}:{node.lineno}] {node.name} is {length} lines (max {args.max_lines})'
                    print(msg)  # print-detection: disable
                    ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
