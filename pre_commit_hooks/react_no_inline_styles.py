#!/usr/bin/python3
"""Hook to detect inline styles in React/JSX files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect `style={{...}}` inline styles in React/JSX/TSX files."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s*//'),
        disable_comment=re.compile(r'react-no-inline-styles\s*:\s*disable'),
        pattern=re.compile(r'style\s*=\s*\{\{'),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
