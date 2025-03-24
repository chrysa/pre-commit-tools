#!/usr/bin/python3
from __future__ import annotations

import re

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s{0,}// \s{0,}console.table\('),
        disable_comment=re.compile(r'console-debtableug-detection\s*:\s*disable'),
        pattern=re.compile(r'^\s{0,}console.table\('),
    )
    return pattern_detection.detect()


if __name__ == '__main__':
    raise SystemExit(main())
