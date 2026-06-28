#!/usr/bin/python3
"""Stage generated files into the git index."""

from __future__ import annotations

import subprocess


def git_add(paths: list[str]) -> None:
    """Stage the given paths; no-op when the list is empty."""
    if not paths:
        return
    subprocess.run(['git', 'add', '--', *paths], check=False)
