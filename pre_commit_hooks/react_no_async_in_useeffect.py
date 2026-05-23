#!/usr/bin/python3
"""Hook to detect async function passed directly to useEffect()."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'\buseEffect\s*\(\s*async\s*(?:\(|\b)')
_COMMENTED = re.compile(r'^\s*//.*\buseEffect\s*\(\s*async')
_DISABLE = re.compile(r'react-no-async-in-useeffect\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect async functions directly passed to useEffect and return 1 if found."""
    pattern_detection = PatternDetection(
        commented=_COMMENTED,
        disable_comment=_DISABLE,
        pattern=_PATTERN,
    )
    return pattern_detection.detect(argv=argv, help_msg='detect async useEffect calls')


if __name__ == '__main__':
    raise SystemExit(main())
