#!/usr/bin/python3
"""Shared factory for the `console.<method>()` detection hooks."""

from __future__ import annotations

import re

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def console_call_detection(*, method: str, disable_id: str) -> PatternDetection:
    """Build a detector for `console.<method>(` calls anywhere on a line.

    The call may follow other code (`cond && console.log(x)`); a line starting with `//`
    or a call placed after a `//` comment marker counts as commented out.
    """
    call = rf'(?<![\w.$])console\.{re.escape(method)}\s*\('
    return PatternDetection(
        commented=re.compile(rf'^\s*//|//.*{call}'),
        disable_comment=re.compile(rf'{re.escape(disable_id)}\s*:\s*disable'),
        pattern=re.compile(call),
    )
