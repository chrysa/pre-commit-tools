#!/usr/bin/python3
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pre_commit_hooks.tools.pattern_detection import PatternDetection

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s{0,}// \s{0,}console.debug\('),
        disable_comment=re.compile(r'console-debug-detection\s*:\s*disable'),
        pattern=re.compile(r'^\s{0,}console.debug\('),
    )
    return pattern_detection.detect()


if __name__ == '__main__':
    raise SystemExit(main())
