#!/usr/bin/python3
"""Hook to detect console.error() calls in JavaScript/TypeScript/JSX/TSX files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented console.error() calls and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s{0,}//\s*console\.error\('),
        disable_comment=re.compile(r'console-error-detection\s*:\s*disable'),
        pattern=re.compile(r'^\s{0,}console\.error\('),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
