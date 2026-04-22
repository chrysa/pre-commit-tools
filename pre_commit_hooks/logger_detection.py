#!/usr/bin/python3
"""Hook to detect direct use of the root logging module instead of a named logger."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect direct root logging calls and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(
            r'#\s*logging\.(debug|info|warning|error|critical|exception)\s*\(',
        ),
        disable_comment=re.compile(r'\blogger-detection\s*:\s*disable'),
        pattern=re.compile(
            r'\blogging\.(debug|info|warning|error|critical|exception)\s*\(',
        ),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
