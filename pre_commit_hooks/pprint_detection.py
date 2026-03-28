#!/usr/bin/python3
"""Hook to detect pprint() calls in Python files."""
from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented pprint() calls and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'#\s*pprint\('),
        disable_comment=re.compile(r'\bpprint-detection\s*:\s*disable'),
        pattern=re.compile(r'\bpprint\('),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
