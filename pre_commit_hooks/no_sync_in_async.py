#!/usr/bin/python3
"""Hook to detect synchronous blocking calls inside async functions."""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, int, str]

# Blocking calls that should not appear inside async functions
_BLOCKING_CALLS: dict[str, str] = {
    'time.sleep': 'use asyncio.sleep instead',
    'requests.get': 'use httpx.AsyncClient or aiohttp',
    'requests.post': 'use httpx.AsyncClient or aiohttp',
    'requests.put': 'use httpx.AsyncClient or aiohttp',
    'requests.delete': 'use httpx.AsyncClient or aiohttp',
    'requests.patch': 'use httpx.AsyncClient or aiohttp',
    'requests.request': 'use httpx.AsyncClient or aiohttp',
    'urllib.request.urlopen': 'use httpx.AsyncClient or aiohttp',
    'subprocess.run': 'use asyncio.create_subprocess_exec',
    'subprocess.call': 'use asyncio.create_subprocess_exec',
    'subprocess.check_output': 'use asyncio.create_subprocess_exec',
    'input': 'use aioconsole or run_in_executor',
}


def _is_disable_comment(source_lines: list[str], lineno: int) -> bool:
    """Return True if the line has a no-sync-in-async disable comment."""
    idx = lineno - 1
    if 0 <= idx < len(source_lines):
        return 'no-sync-in-async: disable' in source_lines[idx]
    return False


def _build_call_name(node: ast.Call) -> str | None:
    """Extract dotted call name from a Call node (e.g. 'time.sleep')."""
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f'{func.value.id}.{func.attr}'
    if isinstance(func, ast.Name):
        return func.id
    return None


def _check_async_body(
    body: list[ast.stmt],
    filename: str,
    source_lines: list[str],
) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if not isinstance(node, ast.Call):
            continue
        name = _build_call_name(node)
        if name and name in _BLOCKING_CALLS:
            lineno = node.lineno
            if not _is_disable_comment(source_lines, lineno):
                hint = _BLOCKING_CALLS[name]
                violations.append((filename, lineno, f'blocking call {name!r} inside async function — {hint}'))
    return violations


class _SyncInAsyncVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self._filename = filename
        self._source_lines = source_lines
        self.violations: list[Violation] = []

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.violations.extend(_check_async_body(node.body, self._filename, self._source_lines))
        self.generic_visit(node)


def detect_sync_in_async(source: str, filename: str) -> list[Violation]:
    """Return violations for blocking calls found inside async functions."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    lines = source.splitlines()
    visitor = _SyncInAsyncVisitor(filename=filename, source_lines=lines)
    visitor.visit(tree)
    return visitor.violations


def main(argv: Sequence[str] | None = None) -> int:
    """Check files for blocking calls inside async functions."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect sync calls inside async functions')
    args, _ = tools.get_args(argv=argv)
    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_sync_in_async(source, filename):
            print(f'{fname}:{lineno}: {msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
