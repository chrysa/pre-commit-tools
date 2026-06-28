#!/usr/bin/python3
"""Hook to detect Sentry send_default_pii=True (RGPD: PII must not be sent to Sentry)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'send_default_pii\s*=\s*True')
_COMMENTED = re.compile(r'^\s*#.*send_default_pii')
_DISABLE = re.compile(r'sentry-pii\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect send_default_pii=True and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect Sentry send_default_pii=True')


if __name__ == '__main__':
    raise SystemExit(main())
