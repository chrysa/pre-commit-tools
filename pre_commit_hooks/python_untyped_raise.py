#!/usr/bin/python3
"""Hook to detect raises of builtin, non-domain exception types in Python files.

The chrysa standard "Raised errors are typed" requires a domain-specific exception
class per bounded context. Raising a bare builtin (`Exception`, `RuntimeError`, …)
gives the caller nothing to catch narrowly and no stable machine-readable code.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, int, str]

# Builtin exception types too generic to carry a domain contract.
_UNTYPED_EXCEPTIONS = frozenset(
    {
        'BaseException',
        'Exception',
        'RuntimeError',
        'StandardError',
    },
)

_DISABLE = 'python-untyped-raise: disable'


def _is_disable_comment(source_lines: list[str], lineno: int) -> bool:
    """Return True if the raise line carries the disable comment."""
    idx = lineno - 1
    if 0 <= idx < len(source_lines):
        return _DISABLE in source_lines[idx]
    return False


def _raised_name(node: ast.Raise) -> str | None:
    """Extract the exception name from a raise statement, if it is a plain name."""
    exc = node.exc
    if exc is None:  # bare `raise` — re-raises the active exception, legitimate
        return None
    if isinstance(exc, ast.Call):
        exc = exc.func
    if isinstance(exc, ast.Name):
        return exc.id
    return None


class _UntypedRaiseVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self._filename = filename
        self._source_lines = source_lines
        self.violations: list[Violation] = []

    def visit_Raise(self, node: ast.Raise) -> None:
        name = _raised_name(node)
        if (
            name in _UNTYPED_EXCEPTIONS
            and not _is_disable_comment(self._source_lines, node.lineno)
        ):
            self.violations.append(
                (
                    self._filename,
                    node.lineno,
                    f'raise of untyped builtin {name!r} — '
                    'raise a domain-specific exception class instead',
                ),
            )
        self.generic_visit(node)


def detect_untyped_raise(source: str, filename: str) -> list[Violation]:
    """Return violations for raises of generic builtin exception types."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    visitor = _UntypedRaiseVisitor(filename=filename, source_lines=source.splitlines())
    visitor.visit(tree)
    return visitor.violations


def main(argv: Sequence[str] | None = None) -> int:
    """Check files for raises of generic builtin exception types."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect raises of untyped builtin exceptions')
    args, _ = tools.get_args(argv=argv)
    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_untyped_raise(source, filename):
            print(f'{fname}:{lineno}: {msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
