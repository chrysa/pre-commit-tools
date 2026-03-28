#!/usr/bin/python3
"""Hook to detect print() calls in Django migration files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect print() calls in migration files and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s*#\s*print\('),
        disable_comment=re.compile(r'no-print-in-migration\s*:\s*disable'),
        pattern=re.compile(r'^\s*print\('),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
