#!/usr/bin/python3
"""Hook to detect a managed skill/agent copy that has drifted from its canonical source.

The transverse skills (``.claude/skills/<name>/``) and the generic agents
(``.claude/agents/<name>.md`` and the ``templates/claude/agents`` staging) are a single
source fanned out to every repo as managed copies by ``distribute-standards.sh``. They must
never be hand-edited in a copy: an edit there drifts silently and the agent then loads a
copy that no longer matches the canon — measured 2026-08, nothing enforced it.

Canonical sources (first hit wins, so it works from any repo in the fleet layout):

* explicit env — ``STD_ROOT`` (skills) / ``AGENTS_REGISTRY`` (agents),
* the current repo itself when it *is* the source (self-compare is skipped),
* a sibling checkout next to the repo root (``../shared-standards`` / ``../agent-config``).

Host-native and graceful: when a source cannot be located the matching check is *skipped*
with a message — best-effort locally, enforced in CI over the fleet checkout. It never
spins up a container and never blocks on a missing sibling.
"""

from __future__ import annotations

import argparse
import filecmp
import os
from collections.abc import Sequence
from pathlib import Path

SKILLS_REL = Path('.claude') / 'skills'
AGENT_DIRS_REL = (Path('.claude') / 'agents', Path('templates') / 'claude' / 'agents')
FIX_HINT = (
    '  A managed copy was edited instead of its source.\n'
    '  Edit the SOURCE (shared-standards/.claude/skills or agent-config/.claude/agents),\n'
    '  then re-run: shared-standards/scripts/distribute-standards.sh '
    '(or check-skills-agents.sh --sync).'
)


def _resolve(repo_root: Path, name: str, override: str | None) -> Path | None:
    if override and Path(override).is_dir():
        return Path(override)
    if repo_root.name == name:
        return repo_root
    sibling = repo_root.parent / name
    return sibling if sibling.is_dir() else None


def _dir_identical(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.funny_files or cmp.diff_files:
        return False
    return all(_dir_identical(a / sub, b / sub) for sub in cmp.common_dirs)


def _drifted_skills(repo_root: Path, src_root: Path) -> list[str]:
    copy_dir, src_dir = repo_root / SKILLS_REL, src_root / SKILLS_REL
    if not copy_dir.is_dir() or copy_dir == src_dir:
        return []
    drift = []
    for path in sorted(copy_dir.iterdir()):
        src = src_dir / path.name
        if path.is_dir() and src.is_dir() and not _dir_identical(src, path):
            drift.append(f'drift [skills]: {path} differs from source {src}')
    return drift


def _agent_source(agents_root: Path) -> Path | None:
    for candidate in (agents_root / '.claude' / 'agents', agents_root / 'agents'):
        if candidate.is_dir():
            return candidate
    return None


def _drifted_agents(repo_root: Path, agents_root: Path) -> list[str]:
    src_dir = _agent_source(agents_root)
    if src_dir is None:
        return []
    drift = []
    for rel in AGENT_DIRS_REL:
        copy_dir = repo_root / rel
        if not copy_dir.is_dir() or copy_dir == src_dir:
            continue
        for md in sorted(copy_dir.glob('*.md')):
            src = src_dir / md.name
            if src.is_file() and not filecmp.cmp(src, md, shallow=False):
                drift.append(f'drift [agents]: {md} differs from source {src}')
    return drift


def main(argv: Sequence[str] | None = None) -> int:
    """Fail when a managed skill/agent copy diverges from its canonical source."""
    parser = argparse.ArgumentParser(description='detect drift of managed skill/agent copies')
    parser.add_argument('filenames', nargs='*', help='ignored — the check is repository-wide')
    parser.add_argument('--root', default='.', help='repository root (default: current directory)')
    args = parser.parse_args(argv)

    repo_root = Path(args.root).resolve()
    drift: list[str] = []

    if (repo_root / SKILLS_REL).is_dir():
        std_root = _resolve(repo_root, 'shared-standards', os.environ.get('STD_ROOT'))
        if std_root is None:
            print(  # print-detection: disable
                'skip [skills]: canonical source (shared-standards) not found — enforced in CI',
            )
        else:
            drift += _drifted_skills(repo_root, std_root)

    if any((repo_root / rel).is_dir() for rel in AGENT_DIRS_REL):
        agents_root = _resolve(repo_root, 'agent-config', os.environ.get('AGENTS_REGISTRY'))
        if agents_root is None:
            print('skip [agents]: registry (agent-config) not found — enforced in CI')  # print-detection: disable
        else:
            drift += _drifted_agents(repo_root, agents_root)

    if not drift:
        return 0
    print('\n'.join(drift))  # print-detection: disable
    print(FIX_HINT)  # print-detection: disable
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
