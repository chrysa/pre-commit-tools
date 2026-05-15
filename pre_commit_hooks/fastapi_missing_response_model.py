#!/usr/bin/python3
"""Hook to detect FastAPI routes missing a response_model parameter."""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, int, str]

# FastAPI router method names
_ROUTE_METHODS = frozenset({'get', 'post', 'put', 'delete', 'patch', 'head', 'options'})


def _is_disable_comment(source_lines: list[str], lineno: int) -> bool:
    idx = lineno - 1
    if 0 <= idx < len(source_lines):
        return 'fastapi-missing-response-model: disable' in source_lines[idx]
    return False


def _get_decorator_call_name(node: ast.expr) -> tuple[str | None, str | None]:
    """Return (object_name, method_name) for a decorator call like @app.get(...)."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        attr = node.func
        if isinstance(attr.value, ast.Name):
            return attr.value.id, attr.attr
    return None, None


def _has_keyword(node: ast.Call, keyword: str) -> bool:
    return any(kw.arg == keyword for kw in node.keywords)


def detect_missing_response_model(source: str, filename: str) -> list[Violation]:
    """Return violations for FastAPI routes without response_model."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    lines = source.splitlines()
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            _obj, method = _get_decorator_call_name(dec)
            if method not in _ROUTE_METHODS:
                continue
            # Found a route decorator — check for response_model keyword
            if not _has_keyword(dec, 'response_model'):
                lineno = dec.lineno
                if not _is_disable_comment(lines, lineno):
                    violations.append(
                        (
                            filename,
                            node.lineno,
                            f'FastAPI route {node.name!r} missing response_model= parameter',
                        ),
                    )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Check Python files for FastAPI routes without response_model."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect FastAPI routes missing response_model')
    args, _ = tools.get_args(argv=argv)
    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_missing_response_model(source, filename):
            print(f'{fname}:{lineno}: {msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
