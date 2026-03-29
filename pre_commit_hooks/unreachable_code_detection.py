#!/usr/bin/python3
"""Hook to detect unreachable code (statements after return/raise/break/continue)."""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

_TERMINAL_NODES: tuple[type[ast.stmt], ...] = (ast.Return, ast.Raise, ast.Break, ast.Continue)

Violation = tuple[str, int, str]


def _check_body(
    body: list[ast.stmt],
    filename: str,
    source_lines: list[str],
) -> list[Violation]:
    """Return violations for unreachable statements in a flat block."""
    violations: list[Violation] = []
    for i, node in enumerate(body):
        if isinstance(node, _TERMINAL_NODES) and i + 1 < len(body):
            next_node = body[i + 1]
            line_idx = next_node.lineno - 1
            if 0 <= line_idx < len(source_lines) and '# unreachable-code: disable' in source_lines[line_idx]:
                break
            stmt_type = type(node).__name__.lower()
            violations.append((filename, next_node.lineno, f'unreachable code after {stmt_type}'))
            break  # report only the first dead statement per block
    return violations


class _UnreachableVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self._filename: str = filename
        self._source_lines: list[str] = source_lines
        self.violations: list[Violation] = []

    def _visit_body(self, body: list[ast.stmt]) -> None:
        self.violations.extend(_check_body(body, self._filename, self._source_lines))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_body(node.body)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    def visit_For(self, node: ast.For) -> None:
        self._visit_body(node.body)
        self.generic_visit(node)

    visit_AsyncFor = visit_For  # noqa: N815

    def visit_While(self, node: ast.While) -> None:
        self._visit_body(node.body)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._visit_body(node.body)
        if node.orelse:
            self._visit_body(node.orelse)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_body(node.body)
        self.generic_visit(node)

    visit_AsyncWith = visit_With  # noqa: N815

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_body(node.body)
        for handler in node.handlers:
            self._visit_body(handler.body)
        if node.orelse:
            self._visit_body(node.orelse)
        if node.finalbody:
            self._visit_body(node.finalbody)
        self.generic_visit(node)

    if sys.version_info >= (3, 11):

        def visit_TryStar(self, node: ast.AST) -> None:  # noqa: N802
            """Handle Python 3.11+ except* syntax."""
            body: list[ast.stmt] = getattr(node, 'body', [])
            if body:
                self._visit_body(body)
            for handler in getattr(node, 'handlers', []):
                handler_body: list[ast.stmt] = getattr(handler, 'body', [])
                if handler_body:
                    self._visit_body(handler_body)
            self.generic_visit(node)


def main(argv: Sequence[str] | None = None) -> int:
    """Detect unreachable code in Python files and return 1 if any violation is found."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='detect unreachable code in Python files')
    args, _ = tools_instance.get_args(argv=argv)
    ret_val = 0
    for filename in args.filenames:
        path = Path(filename)
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=filename)
        except SyntaxError:
            continue
        visitor = _UnreachableVisitor(filename, source.splitlines())
        visitor.visit(tree)
        for fname, lineno, msg in visitor.violations:
            print(f'[{fname}:{lineno}] {msg}')  # print-detection: disable
            ret_val = 1
    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
