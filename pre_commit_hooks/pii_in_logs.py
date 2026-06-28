#!/usr/bin/python3
"""Hook to detect PII (email/token/password/card/ssn/iban/phone) in logging calls (RGPD)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(
    r'(?:\b(?:logger|logging|log)\s*\.\s*(?:debug|info|warning|error|critical|exception)|\bprint)\s*\('
    r'.*\b(email|password|passwd|token|card|ssn|nir|iban|phone)\b',
    re.IGNORECASE,
)
_COMMENTED = re.compile(r'^\s*#')
_DISABLE = re.compile(r'pii-in-logs\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect PII identifiers inside logging calls and return 1 if found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect PII in logging calls')


if __name__ == '__main__':
    raise SystemExit(main())
