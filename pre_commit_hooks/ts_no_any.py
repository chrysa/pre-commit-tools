#!/usr/bin/python3
"""Hook to detect `any` type usage in TypeScript files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect explicit `any` type annotations in TypeScript files."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s*//'),
        disable_comment=re.compile(r'ts-no-any\s*:\s*disable'),
        pattern=re.compile(r':\s*any\b|as\s+any\b|<\s*any\s*>'),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
