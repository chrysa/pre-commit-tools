#!/usr/bin/python3
"""Hook to detect wildcard CORS configuration (allow_origins=['*'] / CORS_ALLOW_ALL_ORIGINS=True)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'allow_origins\s*=\s*\[\s*[\'"]\*[\'"]\s*\]|CORS_ALLOW_ALL_ORIGINS\s*=\s*True')
_COMMENTED = re.compile(r'^\s*(#|//).*(allow_origins|CORS_ALLOW_ALL_ORIGINS)')
_DISABLE = re.compile(r'cors-allow-all\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect wildcard CORS config and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect wildcard CORS configuration')


if __name__ == '__main__':
    raise SystemExit(main())
