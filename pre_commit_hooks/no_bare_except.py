#!/usr/bin/python3
"""Hook to detect bare `except:` clauses (without exception type) in Python files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect bare except: clauses and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s*#\s*except\s*:'),
        disable_comment=re.compile(r'no-bare-except\s*:\s*disable'),
        pattern=re.compile(r'^\s*except\s*:'),
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
