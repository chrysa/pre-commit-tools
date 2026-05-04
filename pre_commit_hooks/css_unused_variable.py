#!/usr/bin/python3
"""Hook to detect CSS custom properties (--var) declared but never used."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

_DISABLE_COMMENT = '/* css-unused-variable: disable */'
_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)
_DECL_RE = re.compile(r'--([a-zA-Z][\w-]*)\s*:')
_USAGE_RE = re.compile(r'var\(\s*--([a-zA-Z][\w-]*)')

Violation = tuple[str, int, str]


def detect_unused_variables(source: str, filename: str) -> list[Violation]:
    """Detect CSS custom properties declared but never used via var()."""
    # Strip block comments before analysis (but keep line numbers)
    lines = source.splitlines()
    # Build a comment-stripped version while tracking line numbers
    stripped_lines = list(_COMMENT_RE.sub('', source).splitlines())

    # Collect declarations: {var_name: lineno}
    declared: dict[str, int] = {}
    for lineno, line in enumerate(stripped_lines, start=1):
        if _DISABLE_COMMENT in lines[lineno - 1]:
            continue
        for m in _DECL_RE.finditer(line):
            var_name = m.group(1)
            if var_name not in declared:
                declared[var_name] = lineno

    # Collect all usages
    used: set[str] = set()
    for line in stripped_lines:
        for m in _USAGE_RE.finditer(line):
            used.add(m.group(1))

    violations: list[Violation] = []
    for var_name, lineno in sorted(declared.items(), key=lambda x: x[1]):
        if var_name not in used:
            violations.append((filename, lineno, f'CSS custom property --{var_name} declared but never used'))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect unused CSS custom properties and return 1 if any are found."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect unused CSS custom properties')
    args, _ = tools.get_args(argv=argv)

    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_unused_variables(source, filename):
            print(f'{fname}:{lineno}: {msg}')  # print-detection: disable
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
