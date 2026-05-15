#!/usr/bin/python3
"""Hook to detect direct DOM manipulation (document.getElementById etc.) in React files."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection

# Matches document.getElementById, document.querySelector[All],
# document.getElementsByClassName/TagName/Name
_DOM_PATTERN = re.compile(
    r'document\.(getElementById|querySelector(?:All)?|getElementsBy(?:ClassName|TagName|Name))\(',
)
_DOM_COMMENTED = re.compile(
    r'^\s*//.*document\.(getElementById|querySelector(?:All)?|getElementsBy(?:ClassName|TagName|Name))\(',
)


def main(argv: Sequence[str] | None = None) -> int:
    """Detect direct DOM manipulation calls and return 1 if any are found."""
    pattern_detection = PatternDetection(
        commented=_DOM_COMMENTED,
        disable_comment=re.compile(r'react-direct-dom\s*:\s*disable'),
        pattern=_DOM_PATTERN,
    )
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
