#!/usr/bin/python3
"""Hook to detect dead/unused code using vulture.

On top of vulture's static analysis this hook adds two capabilities:

* **Dynamic-import awareness** (default-on): names reached only through
  ``importlib.import_module``, ``__import__``, ``getattr``/``setattr``/``hasattr``,
  ``globals()``/``vars()``/``locals()`` subscripts or ``entry_points`` are collected
  from the AST and filtered out of vulture's report, killing false positives.
  Disable with ``--no-dynamic-imports``.
* **Test-only detection** (``--detect-test-only``): symbols defined in production
  code but referenced *only* from test files are flagged separately. Fails the hook
  by default; ``--warn-only`` downgrades these findings to a report.
"""

from __future__ import annotations

import ast
import fnmatch
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

DEFAULT_TEST_PATTERNS = ('tests/', 'test_*.py', '*_test.py', 'conftest.py')


def _iter_python_files(paths: Iterable[str]) -> list[str]:
    """Expand the given paths into a de-duplicated, ordered list of .py files."""
    files: list[str] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(str(f) for f in sorted(path.rglob('*.py')))
        elif path.suffix == '.py':
            files.append(str(path))
    return list(dict.fromkeys(files))


def _const_str(node: ast.expr) -> str | None:
    """Return the string value of a literal node, or None if it is not a str literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _add_name(names: set[str], value: str | None) -> None:
    """Add a dynamic reference and its last dotted segment to the name set."""
    if value:
        names.add(value)
        names.add(value.rsplit('.', 1)[-1])


def _handle_call(node: ast.Call, names: set[str]) -> None:
    """Collect dynamically referenced names from a function/method call."""
    func = node.func
    if isinstance(func, ast.Name):
        fname = func.id
    elif isinstance(func, ast.Attribute):
        fname = func.attr
    else:
        return

    if fname in {'import_module', '__import__'}:
        if node.args:
            _add_name(names, _const_str(node.args[0]))
    elif fname in {'getattr', 'setattr', 'hasattr'}:
        if len(node.args) >= 2:
            _add_name(names, _const_str(node.args[1]))
    elif fname == 'entry_points':
        for arg in node.args:
            _add_name(names, _const_str(arg))
        for kw in node.keywords:
            _add_name(names, _const_str(kw.value))


def _handle_subscript(node: ast.Subscript, names: set[str]) -> None:
    """Collect names from globals()/vars()/locals() string subscripts."""
    value = node.value
    if not isinstance(value, ast.Call):
        return
    func = value.func
    if isinstance(func, ast.Name) and func.id in {'globals', 'vars', 'locals'}:
        _add_name(names, _const_str(node.slice))


def _extract_dynamic_names(tree: ast.AST) -> set[str]:
    """Walk an AST and return every dynamically referenced name."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _handle_call(node, names)
        elif isinstance(node, ast.Subscript):
            _handle_subscript(node, names)
    return names


def collect_dynamic_names(paths: Iterable[str]) -> set[str]:
    """Scan the given paths for names referenced via dynamic imports/attribute access."""
    names: set[str] = set()
    for file in _iter_python_files(paths):
        try:
            source = Path(file).read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError):
            continue
        names |= _extract_dynamic_names(tree)
    return names


def is_test_file(path: str, patterns: Sequence[str] = DEFAULT_TEST_PATTERNS) -> bool:
    """Return True if path matches any test pattern (directory fragment or basename glob)."""
    parsed = Path(path)
    parts = parsed.as_posix().split('/')
    for pattern in patterns:
        if pattern.endswith('/'):
            if pattern.rstrip('/') in parts:
                return True
        elif fnmatch.fnmatch(parsed.name, pattern):
            return True
    return False


def _item_key(item: Any) -> tuple[str, str, int]:
    """Stable identity for a vulture unused-code item."""
    return (str(item.filename), str(item.name), int(item.first_lineno))


def _run_vulture(
    vulture_mod: Any,
    paths: list[str],
    exclude: list[str],
    min_confidence: int,
) -> list[Any]:
    """Run a fresh vulture scan over paths and return the unused-code items."""
    scanner = vulture_mod.Vulture()
    scanner.scavenge(paths, exclude=exclude or [])
    return list(scanner.get_unused_code(min_confidence=min_confidence))


def _filter_dynamic(items: list[Any], dynamic_names: set[str]) -> list[Any]:
    """Drop items whose name is referenced dynamically elsewhere."""
    if not dynamic_names:
        return items
    return [item for item in items if item.name not in dynamic_names]


def _build_parser(tools_instance: Any) -> None:
    """Configure the argument parser for this hook."""
    tools_instance.set_params(
        help_msg='detect dead/unused code using vulture',
        arguments=[
            (
                '--min-confidence',
                {
                    'type': int,
                    'default': 80,
                    'help': 'Minimum confidence percentage for unused code reports (default: 80)',
                },
            ),
            (
                '--exclude',
                {
                    'nargs': '*',
                    'default': [],
                    'metavar': 'PATTERN',
                    'help': 'Glob patterns of paths to exclude (e.g. tests/ migrations/)',
                },
            ),
            (
                '--whitelist',
                {
                    'nargs': '*',
                    'default': [],
                    'metavar': 'FILE',
                    'help': 'Vulture whitelist Python files listing used names to suppress false positives',
                },
            ),
            (
                '--no-dynamic-imports',
                {
                    'action': 'store_true',
                    'help': 'Disable dynamic-import awareness (report names reached via importlib/getattr/...)',
                },
            ),
            (
                '--detect-test-only',
                {
                    'action': 'store_true',
                    'help': 'Also flag production symbols referenced only from test files',
                },
            ),
            (
                '--test-pattern',
                {
                    'nargs': '*',
                    'default': list(DEFAULT_TEST_PATTERNS),
                    'metavar': 'PATTERN',
                    'help': 'File patterns marking test files (default: tests/ test_*.py *_test.py conftest.py)',
                },
            ),
            (
                '--warn-only',
                {
                    'action': 'store_true',
                    'help': 'Report test-only findings without failing the hook',
                },
            ),
        ],
    )


def _report_dead(items: list[Any]) -> None:
    """Print regular dead-code findings."""
    for item in items:
        print(
            f'[{item.filename}:{item.first_lineno}] unused {item.typ}: {item.name}',
        )  # print-detection: disable


def _report_test_only(items: list[Any]) -> None:
    """Print test-only findings."""
    for item in items:
        print(
            f'[{item.filename}:{item.first_lineno}] test-only {item.typ}: {item.name} (used only in tests)',
        )  # print-detection: disable


def main(argv: Sequence[str] | None = None) -> int:
    """Run vulture to detect unused code and return 1 if any is found."""
    try:
        import vulture as _vulture
    except ImportError:
        print(
            'vulture is required: pip install vulture  (or add it to additional_dependencies)',
        )  # print-detection: disable
        return 1

    from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

    tools_instance = PreCommitTools()
    _build_parser(tools_instance)
    args, _ = tools_instance.get_args(argv=argv)

    whitelist = list(args.whitelist)
    filenames = [str(p) for p in args.filenames]
    dynamic_names: set[str] = set() if args.no_dynamic_imports else collect_dynamic_names(whitelist + filenames)

    if args.detect_test_only:
        py_files = _iter_python_files(filenames)
        prod_files = [f for f in py_files if not is_test_file(f, args.test_pattern)]
        unused_full = _filter_dynamic(
            _run_vulture(_vulture, whitelist + py_files, args.exclude, args.min_confidence),
            dynamic_names,
        )
        unused_prod = _filter_dynamic(
            _run_vulture(_vulture, whitelist + prod_files, args.exclude, args.min_confidence),
            dynamic_names,
        )
        full_keys = {_item_key(i) for i in unused_full}
        test_only = [i for i in unused_prod if _item_key(i) not in full_keys]
        _report_dead(unused_full)
        _report_test_only(test_only)
        failed = bool(unused_full) or (bool(test_only) and not args.warn_only)
        return int(failed)

    unused = _filter_dynamic(
        _run_vulture(_vulture, whitelist + filenames, args.exclude, args.min_confidence),
        dynamic_names,
    )
    _report_dead(unused)
    return int(bool(unused))


if __name__ == '__main__':
    raise SystemExit(main())
