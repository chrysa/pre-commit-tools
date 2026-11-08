#!/usr/bin/python3
"""Hook to detect console.warn() calls in JavaScript/TypeScript/React files."""

from __future__ import annotations

from collections.abc import Sequence

from pre_commit_hooks.tools.console_detection import console_call_detection
from pre_commit_hooks.tools.deprecation import warn_deprecated


def main(argv: Sequence[str] | None = None) -> int:
    """Detect uncommented console.warn() calls and return 1 if any are found."""
    warn_deprecated(hook_id='no-console-warn')
    pattern_detection = console_call_detection(method='warn', disable_id='no-console-warn')
    return pattern_detection.detect(argv=argv)


if __name__ == '__main__':
    raise SystemExit(main())
