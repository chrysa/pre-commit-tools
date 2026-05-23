#!/usr/bin/python3
"""Hook to detect hardcoded localhost/127.0.0.1 URLs in source files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'https?://(localhost|127\.0\.0\.1)(:\d+)?[/\s\'"`]?')
_COMMENTED = re.compile(r'^\s*(#|//).*https?://(localhost|127\.0\.0\.1)')
_DISABLE = re.compile(r'no-hardcoded-localhost\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect hardcoded localhost URLs and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=_COMMENTED,
        disable_comment=_DISABLE,
        pattern=_PATTERN,
    )
    return pattern_detection.detect(argv=argv, help_msg='detect hardcoded localhost URLs')


if __name__ == '__main__':
    raise SystemExit(main())
