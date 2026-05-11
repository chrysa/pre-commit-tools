#!/usr/bin/python3
"""Hook to require a DECISIONS.md update when architecture-sensitive files are added."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
from collections.abc import Sequence
from pathlib import Path

_DEFAULT_TRIGGER_PATTERNS: list[str] = [
    "pyproject.toml",
    "package.json",
    "**/routers/*.py",
    "**/services/*.py",
    "alembic.ini",
    "**/migrations/versions/*.py",
    "docker-compose.yml",
    "Dockerfile",
    "**/workflows/*.yml",
]


def get_added_files() -> list[str]:
    """Return filenames staged as newly added (git diff-filter A) in the index."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--diff-filter=A", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in result.stdout.splitlines() if f]


def matches_any_pattern(filepath: str, patterns: list[str]) -> bool:
    """Return True if filepath matches any fnmatch pattern (full path or basename)."""
    name = Path(filepath).name
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def check_adr_gate(
    staged_files: list[str],
    added_files: list[str],
    trigger_patterns: list[str],
    decisions_file: str = "DECISIONS.md",
    warn_only: bool = False,
) -> int:
    """Run the ADR gate check.

    Parameters
    ----------
    staged_files:
        All files currently staged (from pre-commit argv).
    added_files:
        Files staged as newly added (git diff-filter A).
    trigger_patterns:
        fnmatch patterns for architecture-sensitive files.
    decisions_file:
        Path to the decisions file to check (default: DECISIONS.md).
    warn_only:
        When True, print the warning but return 0 instead of 1.

    Returns
    -------
    0 if no violation (or warn_only), 1 if violation detected.
    """
    triggered = [f for f in added_files if matches_any_pattern(f, trigger_patterns)]

    if not triggered:
        return 0

    if decisions_file in staged_files:
        return 0

    print("[adr-gate] Architecture-sensitive files detected:")  # print-detection: disable
    for filepath in triggered:
        print(f"  + {filepath}")  # print-detection: disable
    print()  # print-detection: disable
    print(  # print-detection: disable
        f"{decisions_file} was not updated. Document this architectural decision before committing.",
    )
    print(f"Run: git add {decisions_file}")  # print-detection: disable

    return 0 if warn_only else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Require DECISIONS.md update when architecture-sensitive files are added."""
    parser = argparse.ArgumentParser(
        description="Require DECISIONS.md update on architecture-sensitive file additions",
    )
    parser.add_argument("filenames", nargs="*", help="staged files passed by pre-commit")
    parser.add_argument(
        "--trigger-patterns",
        default=",".join(_DEFAULT_TRIGGER_PATTERNS),
        help="comma-separated fnmatch patterns for trigger files (default: pyproject.toml,package.json,...)",
    )
    parser.add_argument(
        "--decisions-file",
        default="DECISIONS.md",
        help="path to the decisions file to check (default: DECISIONS.md)",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="print a warning but do not block the commit (exit 0)",
    )
    args = parser.parse_args(argv)

    trigger_patterns = [p.strip() for p in args.trigger_patterns.split(",") if p.strip()]
    added = get_added_files()

    return check_adr_gate(
        staged_files=args.filenames,
        added_files=added,
        trigger_patterns=trigger_patterns,
        decisions_file=args.decisions_file,
        warn_only=args.warn_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
