#!/usr/bin/python3
"""Hook to detect debugger statements in Python files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect debugger statements and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'#\s*(breakpoint\s*\(|pdb\.set_trace\s*\(|ipdb\.set_trace\s*\(|pudb\.set_trace\s*\()'),
        disable_comment=re.compile(r'\bdebugger-detection\s*:\s*disable'),
        pattern=re.compile(r'\b(breakpoint\s*\(|pdb\.set_trace\s*\(|ipdb\.set_trace\s*\(|pudb\.set_trace\s*\()'),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
