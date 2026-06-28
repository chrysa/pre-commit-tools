#!/usr/bin/python3
"""Hook to detect create_all() schema creation outside migrations (migrations are the schema source of truth)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'(?<![\w])(?:\w+\.)?create_all\s*\(')
_COMMENTED = re.compile(r'^\s*(#|//).*create_all\s*\(')
_DISABLE = re.compile(r'no-create-all\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect create_all() calls and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect create_all() outside migrations')


if __name__ == '__main__':
    raise SystemExit(main())
