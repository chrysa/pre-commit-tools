#!/usr/bin/python3
"""Hook to detect console.debug() calls in JavaScript/AppScript files."""

from __future__ import annotations

from collections.abc import Sequence

from pre_commit_hooks.tools.console_detection import console_call_detection
from pre_commit_hooks.tools.deprecation import warn_deprecated


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented console.debug() calls and return 1 if any are found."""
    warn_deprecated(hook_id='console-debug-detection')
    pattern_detection = console_call_detection(method='debug', disable_id='console-debug-detection')
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
