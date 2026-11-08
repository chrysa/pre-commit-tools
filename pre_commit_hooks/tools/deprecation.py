#!/usr/bin/python3
"""Deprecation registry for hooks superseded by a native linter rule.

A deprecated hook keeps working (same exit code, same output) so that no consumer
pipeline breaks on upgrade; it only prints a migration notice on stderr. The full
migration guide lives in DEPRECATIONS.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class Deprecation:
    """Describe how to replace a deprecated hook with a native linter rule."""

    replacement: str
    migration: str


_RUFF = 'ruff (astral-sh/ruff-pre-commit)'
_ESLINT_NO_CONSOLE = Deprecation(
    replacement='ESLint core rule `no-console`',
    migration='"rules": { "no-console": "error" } — allow only what you need with { "allow": [...] }',
)

DEPRECATED_HOOKS: dict[str, Deprecation] = {
    'python-print-detection': Deprecation(
        replacement=f'{_RUFF} rule T201',
        migration='[tool.ruff.lint] extend-select = ["T20"]; inline opt-out: `# noqa: T201`',
    ),
    'python-pprint-detection': Deprecation(
        replacement=f'{_RUFF} rule T203',
        migration='[tool.ruff.lint] extend-select = ["T20"]; inline opt-out: `# noqa: T203`',
    ),
    'debugger-detection': Deprecation(
        replacement=f'{_RUFF} rule T100',
        migration='[tool.ruff.lint] extend-select = ["T10"]; inline opt-out: `# noqa: T100`',
    ),
    'no-print-in-migration': Deprecation(
        replacement=f'{_RUFF} rule T201',
        migration='extend-select = ["T20"] (covers migrations); scope with [tool.ruff.lint.per-file-ignores]',
    ),
    'no-bare-except': Deprecation(
        replacement=f'{_RUFF} rule E722',
        migration='[tool.ruff.lint] extend-select = ["E722"] (included in "E"); opt-out: `# noqa: E722`',
    ),
    'python-mutable-default': Deprecation(
        replacement=f'{_RUFF} rule B006',
        migration='[tool.ruff.lint] extend-select = ["B006"] (included in "B"); opt-out: `# noqa: B006`',
    ),
    'python-logger-detection': Deprecation(
        replacement=f'{_RUFF} rule LOG015',
        migration='[tool.ruff.lint] extend-select = ["LOG"]; inline opt-out: `# noqa: LOG015`',
    ),
    'no-sync-in-async': Deprecation(
        replacement=f'{_RUFF} rules ASYNC210/212/220/221/222/230/251',
        migration='[tool.ruff.lint] extend-select = ["ASYNC"]; `input()` is not covered upstream',
    ),
    'console-log-detection': _ESLINT_NO_CONSOLE,
    'console-debug-detection': _ESLINT_NO_CONSOLE,
    'console-table-detection': _ESLINT_NO_CONSOLE,
    'no-console-warn': _ESLINT_NO_CONSOLE,
    'react-console-error-detection': _ESLINT_NO_CONSOLE,
    'ts-no-any': Deprecation(
        replacement='typescript-eslint rule `@typescript-eslint/no-explicit-any`',
        migration='"rules": { "@typescript-eslint/no-explicit-any": "error" }',
    ),
    'ts-unreachable-code': Deprecation(
        replacement='ESLint core rule `no-unreachable` + tsconfig `allowUnreachableCode: false`',
        migration='"rules": { "no-unreachable": "error" }; tsconfig compilerOptions.allowUnreachableCode = false',
    ),
    'dockerfile-no-latest': Deprecation(
        replacement='hadolint rules DL3007 (`:latest`) and DL3006 (untagged image)',
        migration='add repo hadolint/hadolint, hook `hadolint-docker` (or `hadolint` with a local binary)',
    ),
}

_NOTICE = (
    '[DEPRECATED] hook `{hook_id}` will be removed in a future release.\n'
    '  Replace it with: {replacement}\n'
    '  Migration: {migration}\n'
    '  Full guide: https://github.com/chrysa/pre-commit-tools/blob/develop/DEPRECATIONS.md\n'
)


def warn_deprecated(*, hook_id: str, stream: TextIO | None = None) -> None:
    """Print the migration notice for a deprecated hook on stderr (no-op if unknown)."""
    deprecation = DEPRECATED_HOOKS.get(hook_id)
    if deprecation is None:
        return
    target = sys.stderr if stream is None else stream
    target.write(
        _NOTICE.format(
            hook_id=hook_id,
            replacement=deprecation.replacement,
            migration=deprecation.migration,
        ),
    )
