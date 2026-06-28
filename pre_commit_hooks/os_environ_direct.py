#!/usr/bin/python3
"""Hook to detect direct os.environ / os.getenv access outside settings modules."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

_PATTERN = re.compile(r'os\.environ\b|os\.getenv\s*\(')
_COMMENTED = re.compile(r'^\s*#.*os\.(environ|getenv)')
_DISABLE = re.compile(r'os-environ-direct\s*:\s*disable')


def main(argv: Sequence[str] | None = None) -> int:
    """Detect direct os.environ/os.getenv usage and return 1 if any is found."""
    pattern_detection = PatternDetection(commented=_COMMENTED, disable_comment=_DISABLE, pattern=_PATTERN)
    return pattern_detection.detect(argv=argv, help_msg='detect direct os.environ access outside settings')


if __name__ == '__main__':
    raise SystemExit(main())
