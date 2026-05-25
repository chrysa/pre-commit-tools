#!/usr/bin/python3
"""Hook to detect `# type: ignore` without an explanatory comment."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

# Matches `# type: ignore` (with optional [qualifier]) not followed by another `#` comment
_TYPE_IGNORE_NO_REASON_RE = re.compile(
    r'#\s*type:\s*ignore(?:\[.*?\])?\s*$',
)
_DISABLE_COMMENT = '# python-no-type-ignore: disable'

Violation = tuple[str, int, str]


def detect_bare_type_ignore(source: str, filename: str) -> list[Violation]:
    """Return violations for `# type: ignore` without a following justification comment."""
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _DISABLE_COMMENT in line:
            continue
        if _TYPE_IGNORE_NO_REASON_RE.search(line):
            violations.append(
                (
                    filename,
                    lineno,
                    '# type: ignore without justification comment (add e.g. `# type: ignore[attr-defined]  # reason`)',
                ),
            )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect bare `# type: ignore` and return 1 if any found."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect # type: ignore without justification comment',
    )
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            source = Path(filename).read_text(encoding='utf-8')
        except OSError, UnicodeDecodeError:
            continue
        for fname, lineno, msg in detect_bare_type_ignore(source, filename):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
