#!/usr/bin/python3
"""Hook to detect console.debug() calls in JavaScript/AppScript files."""
from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented console.debug() calls and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s{0,}// \s{0,}console.debug\('),
        disable_comment=re.compile(r'console-debug-detection\s*:\s*disable'),
        pattern=re.compile(r'^\s{0,}console.debug\('),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
