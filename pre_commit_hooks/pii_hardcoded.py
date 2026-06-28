#!/usr/bin/python3
"""Hook to detect hardcoded personal data (NIR, IBAN, real email, FR phone) in source (RGPD)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_NIR = r'\b[12]\d{2}(?:0[1-9]|1[0-2])\d{10}\b'
_IBAN = r'\bFR\d{2}[0-9A-Z]{23}\b'
_EMAIL = r'\b[A-Za-z0-9._%+-]+@(?!example\.|test\.|localhost)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
_PHONE = r'\b0[1-9](?:[ .]?\d{2}){4}\b'

_PATTERN = re.compile(f'{_NIR}|{_IBAN}|{_EMAIL}|{_PHONE}')
_COMMENTED = re.compile(r'^\s*(#|//)')
_DISABLE = re.compile(r'pii-hardcoded\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect hardcoded personal data and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect hardcoded personal data (RGPD)')


if __name__ == '__main__':
    raise SystemExit(main())
