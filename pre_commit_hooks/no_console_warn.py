#!/usr/bin/python3
"""Hook to detect console.warn() calls in JavaScript/TypeScript/React files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented console.warn() calls and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s*//\s*console\.warn\('),
        disable_comment=re.compile(r'no-console-warn\s*:\s*disable'),
        pattern=re.compile(r'^\s*console\.warn\('),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
