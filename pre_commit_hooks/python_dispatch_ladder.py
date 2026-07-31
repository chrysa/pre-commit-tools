#!/usr/bin/python3
"""Hook to detect if/elif ladders that dispatch on one value against constants.

The chrysa standard "Prefer a lookup table to a state machine" requires such
branching to be expressed as a hash table from key to handler or value, so a new
case is a new row rather than an edit to control flow. Only ladders that compare
the *same* expression against constant literals are flagged — a chain of unrelated
conditions is genuine branching, not disguised dispatch.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence

from pre_commit_hooks.tools.source_reader import read_source

Violation = tuple[str, int, str]

_DEFAULT_MAX_BRANCHES = 3
_DISABLE = 'python-dispatch-ladder: disable'


def _is_disabled(source_lines: list[str], lineno: int) -> bool:
    """Return True if the ladder's first line carries the disable comment."""
    idx = lineno - 1
    if 0 <= idx < len(source_lines):
        return _DISABLE in source_lines[idx]
    return False


def _dispatch_subject(test: ast.expr) -> str | None:
    """Return the dumped subject of `<expr> == <constant>` / `<expr> in (...)`, else None.

    The subject is returned as its AST dump so two occurrences of the same
    expression (``self.status``, ``event["kind"]``) compare equal.
    """
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return None
    if not isinstance(test.ops[0], ast.Eq | ast.In):
        return None
    comparator = test.comparators[0]
    if isinstance(test.ops[0], ast.In):
        if not isinstance(comparator, ast.List | ast.Set | ast.Tuple):
            return None
        if not all(isinstance(elt, ast.Constant) for elt in comparator.elts):
            return None
    elif not isinstance(comparator, ast.Constant):
        return None
    return ast.dump(test.left)


def _ladder_subjects(node: ast.If) -> list[str | None]:
    """Walk an if/elif chain and return each branch's dispatch subject."""
    subjects = [_dispatch_subject(node.test)]
    current = node
    while len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
        current = current.orelse[0]
        subjects.append(_dispatch_subject(current.test))
    return subjects


def detect_dispatch_ladder(
    source: str,
    filename: str,
    max_branches: int = _DEFAULT_MAX_BRANCHES,
) -> list[Violation]:
    """Return violations for if/elif ladders dispatching on a single value."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    source_lines = source.splitlines()
    violations: list[Violation] = []
    # Only the head of each chain is inspected; nested `elif` nodes are part of it.
    heads = {
        id(orelse)
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        for orelse in node.orelse
        if isinstance(orelse, ast.If)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or id(node) in heads:
            continue
        subjects = _ladder_subjects(node)
        if len(subjects) <= max_branches or None in subjects:
            continue
        if len(set(subjects)) != 1:
            continue
        if _is_disabled(source_lines, node.lineno):
            continue
        violations.append(
            (
                filename,
                node.lineno,
                f'if/elif ladder dispatching on one value across {len(subjects)} branches '
                f'(max {max_branches}) — replace it with a lookup table (dict) '
                'from key to handler or value',
            ),
        )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Check files for if/elif ladders that should be lookup tables."""
    parser = argparse.ArgumentParser(description='Detect dispatch ladders.')
    parser.add_argument('--max-branches', type=int, default=_DEFAULT_MAX_BRANCHES)
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    retval = 0
    for filename in args.filenames:
        source = read_source(filename)
        if source is None:
            continue
        for fname, lineno, msg in detect_dispatch_ladder(source, filename, args.max_branches):
            print(f'{fname}:{lineno}: {msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
