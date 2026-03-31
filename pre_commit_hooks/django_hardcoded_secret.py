#!/usr/bin/python3
"""Hook to detect hardcoded secrets in Django/Python settings files."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

_DISABLE_COMMENT = '# django-hardcoded-secret: disable'

# Patterns that indicate a hardcoded secret (not an env-var reference)
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ('SECRET_KEY', re.compile(r"""^\s*SECRET_KEY\s*=\s*['"][^'"]{8,}['"]""", re.IGNORECASE)),
    ('PASSWORD', re.compile(r"""^\s*\w*PASSWORD\w*\s*=\s*['"][^'"]{4,}['"]""", re.IGNORECASE)),
    ('API_KEY', re.compile(r"""^\s*\w*API_KEY\w*\s*=\s*['"][^'"]{4,}['"]""", re.IGNORECASE)),
    ('TOKEN', re.compile(r"""^\s*\w*TOKEN\w*\s*=\s*['"][^'"]{4,}['"]""", re.IGNORECASE)),
    ('PRIVATE_KEY', re.compile(r"""^\s*\w*PRIVATE_KEY\w*\s*=\s*['"][^'"]{4,}['"]""", re.IGNORECASE)),
]

# Lines where the value is clearly using env variables — not flagged
_SAFE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'os\.environ'),
    re.compile(r'os\.getenv'),
    re.compile(r'env\('),
    re.compile(r'get_env'),
    re.compile(r'config\('),
    re.compile(r'decouple'),
    re.compile(r'django-environ'),
    re.compile(r'getenv'),
]

Violation = tuple[str, int, str]


def detect_hardcoded_secrets(source: str, filename: str) -> list[Violation]:
    """Detect hardcoded secret assignments in Python source."""
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
    """Detect hardcoded secrets in settings files and return 1 if any are found."""
    tools = PreCommitTools()
    tools.set_params(help_msg='detect hardcoded secrets in Python files')
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
