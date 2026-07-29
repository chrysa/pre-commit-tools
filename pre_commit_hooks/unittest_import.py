#!/usr/bin/python3
"""Hook to detect stdlib unittest imports, which the chrysa standard forbids.

Tests use pytest with assert-style functions and pytest-mock (the `mocker`
fixture) for all mocking. `import unittest` and `from unittest.mock import ...`
are banned; this hook blocks them at write time rather than in review.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'^\s*(?:import\s+unittest(?:\.\w+)*|from\s+unittest(?:\.\w+)*\s+import\s)')
_COMMENTED = re.compile(r'^\s*#.*\bunittest\b')
_DISABLE = re.compile(r'unittest-import\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect stdlib unittest imports and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect forbidden unittest imports (use pytest + pytest-mock)')


if __name__ == '__main__':
    raise SystemExit(main())
