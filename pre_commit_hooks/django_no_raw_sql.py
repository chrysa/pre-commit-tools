#!/usr/bin/python3
"""Hook to detect raw SQL queries in Django code (.raw() and cursor.execute())."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

# Matches .raw( and cursor.execute( — common unsafe raw SQL patterns
_RAW_SQL_PATTERN = re.compile(r'(?:\.raw\(|cursor\.execute\()')
_RAW_SQL_COMMENTED = re.compile(r'^\s*#.*(?:\.raw\(|cursor\.execute\()')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect raw SQL queries and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=_RAW_SQL_COMMENTED,
        disable_comment=re.compile(r'django-no-raw-sql\s*:\s*disable'),
        pattern=_RAW_SQL_PATTERN,
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
