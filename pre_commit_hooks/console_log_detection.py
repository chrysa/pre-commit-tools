#!/usr/bin/python3
"""Hook to detect console.log() calls in JavaScript/AppScript files."""

from __future__ import annotations

from collections.abc import Sequence

from pre_commit_hooks.tools.console_detection import console_call_detection
from pre_commit_hooks.tools.deprecation import warn_deprecated


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented console.log() calls and return 1 if any are found."""
    warn_deprecated(hook_id='console-log-detection')
    pattern_detection = console_call_detection(method='log', disable_id='console-log-detection')
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
