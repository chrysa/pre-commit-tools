#!/usr/bin/python3
"""Hook to detect mutable default arguments in Python function signatures.

A mutable default (`[]`, `{}`, `set()`, …) is evaluated once at definition time and
shared across every call — the classic anti-pattern named by the chrysa standard
"Basic optimisations and known anti-patterns". Use `None` and build inside the body.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, int, str]

# Calls returning a fresh mutable container — same trap as a literal.
_MUTABLE_CALLS = frozenset({'Counter', 'defaultdict', 'deque', 'dict', 'list', 'set'})

_DISABLE = 'python-mutable-default: disable'


def _is_disable_comment(source_lines: list[str], lineno: int) -> bool:
    """Return True if the signature line carries the disable comment."""
    idx = lineno - 1
    if 0 <= idx < len(source_lines):
        return _DISABLE in source_lines[idx]
    return False


def _mutable_kind(node: ast.expr | None) -> str | None:
    """Return a label for the mutable default, or None when the default is safe."""
    if isinstance(node, ast.List):
        return 'list literal'
    if isinstance(node, ast.Dict):
        return 'dict literal'
    if isinstance(node, ast.Set):
        return 'set literal'
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in _MUTABLE_CALLS:
            return f'{node.func.id}() call'
    return None


def _defaults_of(args: ast.arguments) -> list[ast.expr | None]:
    """Return every default expression of a signature, positional and keyword-only."""
    return [*args.defaults, *args.kw_defaults]


def _check_signature(
    node: ast.AsyncFunctionDef | ast.FunctionDef,
    filename: str,
    source_lines: list[str],
) -> list[Violation]:
    violations: list[Violation] = []
    for default in _defaults_of(node.args):
        kind = _mutable_kind(default)
        if kind is None or default is None:
            continue
        lineno = default.lineno
        if _is_disable_comment(source_lines, lineno):
            continue
        violations.append(
            (
                filename,
                lineno,
                f'mutable default argument ({kind}) in {node.name!r} — '
                'default to None and build the value inside the body',
            ),
        )
    return violations


class _MutableDefaultVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self._filename = filename
        self._source_lines = source_lines
        self.violations: list[Violation] = []

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.violations.extend(
            _check_signature(node, self._filename, self._source_lines),
        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.violations.extend(
            _check_signature(node, self._filename, self._source_lines),
        )
        self.generic_visit(node)


def detect_mutable_default(source: str, filename: str) -> list[Violation]:
    """Return violations for mutable default arguments."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    visitor = _MutableDefaultVisitor(filename=filename, source_lines=source.splitlines())
    visitor.visit(tree)
    return visitor.violations


def main(argv: Sequence[str] | None = None) -> int:
    """Check files for mutable default arguments."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect mutable default arguments')
    args, _ = tools.get_args(argv=argv)
    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_mutable_default(source, filename):
            print(f'{fname}:{lineno}: {msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
