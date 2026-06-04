#!/usr/bin/python3
"""Hook to detect FastAPI routes whose response model lacks a 'links' field (HATEOAS)."""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, int, str]

_ROUTE_METHODS = frozenset({'get', 'post', 'put', 'delete', 'patch', 'head', 'options'})
_MODEL_BASE_NAMES = frozenset({'BaseModel', 'BaseSchema', 'BaseResponse', 'Schema'})


def _is_disable_comment(source_lines: list[str], lineno: int) -> bool:
    idx = lineno - 1
    if 0 <= idx < len(source_lines):
        return 'fastapi-missing-links: disable' in source_lines[idx]
    return False


def _get_pydantic_models(tree: ast.Module) -> dict[str, ast.ClassDef]:
    """Return a mapping of class name → ClassDef for Pydantic-like models."""
    models: dict[str, ast.ClassDef] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name = ''
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name in _MODEL_BASE_NAMES or base_name.endswith('Model') or base_name.endswith('Schema'):
                models[node.name] = node
    return models


def _model_has_links(class_def: ast.ClassDef) -> bool:
    """Return True if the class has a 'links' annotated field."""
    for node in ast.walk(class_def):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == 'links':
                return True
    return False


def _get_response_model_name(dec: ast.Call) -> str | None:
    """Extract the class name from response_model=ClassName in a decorator."""
    for kw in dec.keywords:
        if kw.arg == 'response_model':
            if isinstance(kw.value, ast.Name):
                return kw.value.id
            if isinstance(kw.value, ast.Subscript) and isinstance(kw.value.value, ast.Name):
                if kw.value.value.id in {'list', 'List', 'Optional'}:
                    if isinstance(kw.value.slice, ast.Name):
                        return kw.value.slice.id
    return None


def _get_decorator_method(dec: ast.expr) -> str | None:
    """Return method name for @router.get(...) style decorators."""
    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
        return dec.func.attr
    return None


def detect_missing_links(source: str, filename: str) -> list[Violation]:
    """Return violations for FastAPI routes whose response_model lacks a 'links' field."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    lines = source.splitlines()
    models = _get_pydantic_models(tree)
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            method = _get_decorator_method(dec)
            if method not in _ROUTE_METHODS:
                continue
            if _is_disable_comment(lines, dec.lineno):
                continue
            model_name = _get_response_model_name(dec)
            if model_name is None or model_name not in models:
                continue
            if not _model_has_links(models[model_name]):
                violations.append(
                    (
                        filename,
                        node.lineno,
                        f"response model {model_name!r} used in route {node.name!r} has no 'links' field (HATEOAS)",
                    ),
                )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Check Python files for FastAPI response models missing a 'links' field."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect FastAPI response models missing links field (HATEOAS)')
    args, _ = tools.get_args(argv=argv)
    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_missing_links(source, filename):
            print(f'{fname}:{lineno}: {msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
