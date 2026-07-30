#!/usr/bin/python3
"""Hook to detect a chrysa repository whose ``.claude/`` mirror is missing.

The shared skills and agents are distributed as versioned copies into every repo.
Nothing checked that they were still there: a repo whose ``.claude/skills`` had
been wiped kept working, silently, with no skill loaded — the agent simply did a
worse job and said nothing. Measured on 2026-07-29: no CI job, no lint rule and
no hook covered the absence.

A repository is considered in scope when its ``CLAUDE.md`` carries the managed
``chrysa:standards`` block, which is exactly the set of repos the distribution
targets. Anything else is skipped.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

MANAGED_MARKER = 'chrysa:standards:start'
CLAUDE_FILE = 'CLAUDE.md'
SKILLS_DIR = Path('.claude') / 'skills'


def _is_fleet_repo(root: Path) -> bool:
    claude_md = root / CLAUDE_FILE
    if not claude_md.is_file():
        return False
    return MANAGED_MARKER in claude_md.read_text(encoding='utf-8', errors='replace')


def _has_skills(root: Path) -> bool:
    skills = root / SKILLS_DIR
    if not skills.is_dir():
        return False
    return any(skills.glob('*/SKILL.md'))


def main(argv: Sequence[str] | None = None) -> int:
    """Fail when a fleet repository carries no shared skills."""
    parser = argparse.ArgumentParser(description='detect a missing .claude/ mirror')
    parser.add_argument('filenames', nargs='*', help='ignored — the check is repository-wide')
    parser.add_argument('--root', default='.', help='repository root (default: current directory)')
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not _is_fleet_repo(root):
        return 0

    if _has_skills(root):
        return 0

    print(
        f'{root / SKILLS_DIR}: no shared skill found in a repository that carries the managed '
        'chrysa:standards block.\n'
        '  The agent loads .claude/ at session start: an empty mirror means no skill is active, '
        'and nothing else reports it.\n'
        '  Restore it with: shared-standards/scripts/distribute-standards.sh <repo>',
    )
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
