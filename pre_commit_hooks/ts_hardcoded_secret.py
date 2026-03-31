#!/usr/bin/python3
"""Hook to detect hardcoded secrets in TypeScript and JavaScript files."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

_DISABLE_COMMENT = '// ts-hardcoded-secret: disable'

# Patterns that signal hardcoded secrets in TypeScript/JavaScript source
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        'API_KEY',
        re.compile(r"""\w*[Aa][Pp][Ii]_?[Kk][Ee][Yy]\w*\s*[=:]\s*['"`][^'"`]{4,}['"`]"""),
    ),
    (
        'TOKEN',
        re.compile(r"""\w*[Tt][Oo][Kk][Ee][Nn]\w*\s*[=:]\s*['"`][^'"`]{4,}['"`]"""),
    ),
    (
        'PASSWORD',
        re.compile(r"""\w*[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\w*\s*[=:]\s*['"`][^'"`]{4,}['"`]"""),
    ),
    (
        'SECRET',
        re.compile(r"""\w*[Ss][Ee][Cc][Rr][Ee][Tt]\w*\s*[=:]\s*['"`][^'"`]{8,}['"`]"""),
    ),
    (
        'PRIVATE_KEY',
        re.compile(r"""\w*[Pp][Rr][Ii][Vv][Aa][Tt][Ee]_?[Kk][Ee][Yy]\w*\s*[=:]\s*['"`][^'"`]{4,}['"`]"""),
    ),
    ('AWS_KEY', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('GITHUB_TOKEN', re.compile(r'gh[pors]_[A-Za-z0-9]{36,}')),
    ('STRIPE_KEY', re.compile(r'(?:sk|pk)_live_[0-9a-zA-Z]{24,}')),
]

# Lines where the value is clearly env-based — skip these
_SAFE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'process\.env'),
    re.compile(r'import\.meta\.env'),
    re.compile(r'getenv|getEnv'),
    re.compile(r'process\.env\['),
]

Violation = tuple[str, int, str]


def detect_hardcoded_secrets(source: str, filename: str) -> list[Violation]:
    """Detect hardcoded secret assignments in TypeScript/JavaScript source."""
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _DISABLE_COMMENT in line:
            continue
        if any(safe.search(line) for safe in _SAFE_PATTERNS):
            continue
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(line):
                violations.append((filename, lineno, f'hardcoded {label} detected'))
                break
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect hardcoded secrets in TypeScript/JavaScript files and return 1 if any found."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect hardcoded secrets in TypeScript/JavaScript files')
    args, _ = tools.get_args(argv=argv)

    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_hardcoded_secrets(source, filename):
            print(f'{fname}:{lineno}: {msg}')  # print-detection: disable
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
