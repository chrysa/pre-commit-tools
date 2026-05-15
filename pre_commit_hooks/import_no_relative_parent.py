#!/usr/bin/python3
"""Hook to detect deep relative parent imports (../../) in TypeScript/JavaScript files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

# Matches:
# - import ... from '../../...' (ES modules)
# - const x = require('../../...') (CommonJS)
# — at least two levels of parent traversal
_RELATIVE_PARENT = re.compile(
    r"""(?:from\s+['"]|require\s*\(['"])(\.\./){2,}""",
)
_RELATIVE_PARENT_COMMENTED = re.compile(
    r"""^\s*//.*(?:from\s+['"]|require\s*\(['"])(\.\./){2,}""",
)


def main(argv: Sequence[str] | None = None) -> int:
    """Detect deep relative parent imports and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=_RELATIVE_PARENT_COMMENTED,
        disable_comment=re.compile(r'import-no-relative-parent\s*:\s*disable'),
        pattern=_RELATIVE_PARENT,
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
