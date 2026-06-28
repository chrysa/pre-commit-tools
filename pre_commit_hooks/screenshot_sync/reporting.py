#!/usr/bin/python3
"""User-facing warnings and the skip/fail decision for the hooks."""

from __future__ import annotations


def warn(message: str) -> None:
    print(f'[screenshot-sync] {message}')  # print-detection: disable


def skip_or_fail(strict: bool, message: str) -> int:
    """Warn, then return 1 when strict (block the commit) else 0 (skip)."""
    warn(message)
    return 1 if strict else 0
