#!/usr/bin/python3
"""Hook to detect auth tokens stored in localStorage (RGPD: prefer httpOnly cookies)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(
    r'localStorage\.setItem\(\s*[\'"`][^\'"`]*(token|jwt|auth|access|refresh)[^\'"`]*[\'"`]',
    re.IGNORECASE,
)
_COMMENTED = re.compile(r'^\s*//.*localStorage\.setItem')
_DISABLE = re.compile(r'token-localstorage\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect auth tokens written to localStorage and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect auth tokens in localStorage')


if __name__ == '__main__':
    raise SystemExit(main())
