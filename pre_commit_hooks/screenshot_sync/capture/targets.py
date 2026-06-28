#!/usr/bin/python3
"""Shared capture-target type and glob matching helper."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CaptureTarget:
    name: str
    url: str
    full_url: str


def matches(filepath: str, pattern: str) -> bool:
    """Return True if filepath matches pattern on the full path or basename."""
    name = Path(filepath).name
    return fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(name, pattern)
