#!/usr/bin/python3
"""Hook to detect sections in per-repo copilot-instructions.md already present in workspace instructions."""

from __future__ import annotations

import argparse
import difflib
from collections.abc import Sequence
from pathlib import Path

_DISABLE_COMMENT = 'detect-duplicated-copilot-instructions: disable'
_DEFAULT_THRESHOLD = 0.80
_INSTRUCTIONS_REL = Path('.github') / 'copilot-instructions.md'


def extract_sections(text: str) -> dict[str, str]:
    """Return {heading: body} for every H2 section (## Title) in *text*."""
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        if line.startswith('## '):
            if current_heading is not None:
                sections[current_heading] = ''.join(current_lines).strip()
            current_heading = line.strip().lstrip('# ').strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = ''.join(current_lines).strip()

    return sections


def similarity(a: str, b: str) -> float:
    """Return SequenceMatcher ratio between two strings."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_workspace_instructions(repo_file: Path) -> Path | None:
    """Walk up from *repo_file* to find the workspace-level copilot-instructions.md.

    Returns the path if found above the repo's own .github/ directory, else None.
    """
    # The repo_file is e.g. /workspace/chrysa/some-repo/.github/copilot-instructions.md
    # We walk up 3+ levels to find /workspace/.github/copilot-instructions.md
    current = repo_file.resolve().parent.parent  # skip .github/ of the repo
    while True:
        candidate = current / _INSTRUCTIONS_REL
        if candidate.exists() and candidate.resolve() != repo_file.resolve():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def check_duplications(
    repo_file: Path,
    workspace_file: Path,
    threshold: float,
) -> list[tuple[float, str]]:
    """Return list of (ratio, heading) for sections duplicated above *threshold*."""
    repo_text = repo_file.read_text(encoding='utf-8')

    # Respect file-level disable comment
    if _DISABLE_COMMENT in repo_text:
        return []

    repo_sections = extract_sections(repo_text)
    workspace_sections = extract_sections(workspace_file.read_text(encoding='utf-8'))

    duplicates: list[tuple[float, str]] = []
    for heading, body in repo_sections.items():
        if not body:
            continue
        for ws_body in workspace_sections.values():
            ratio = similarity(body, ws_body)
            if ratio >= threshold:
                duplicates.append((ratio, heading))
                break  # one match is enough per heading

    return sorted(duplicates, key=lambda x: x[0], reverse=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Detect duplicated copilot-instructions sections and return 1 if any found."""
    parser = argparse.ArgumentParser(
        description='Detect sections in per-repo copilot-instructions.md already in workspace instructions',
    )
    parser.add_argument('filenames', nargs='*', help='staged files passed by pre-commit')
    parser.add_argument(
        '--threshold',
        type=float,
        default=_DEFAULT_THRESHOLD,
        help='similarity threshold 0-1 above which a section is flagged (default: 0.80)',
    )
    args = parser.parse_args(argv)

    ret_val = 0
    for filename in args.filenames:
        repo_file = Path(filename).resolve()
        if not repo_file.exists():
            continue

        workspace_file = find_workspace_instructions(repo_file)
        if workspace_file is None:
            # No workspace instructions found — pass silently
            continue

        duplicates = check_duplications(repo_file, workspace_file, args.threshold)
        if duplicates:
            print(  # print-detection: disable
                f'[detect-duplicated-copilot-instructions] Found {len(duplicates)} section(s)'
                f' already in workspace instructions ({workspace_file}):',
            )
            for ratio, heading in duplicates:
                print(f'  [{ratio:.0%}] ## {heading}')  # print-detection: disable
            print(  # print-detection: disable
                'Remove them from the per-repo file — keep only repo-specific content.',
            )
            ret_val = 1

    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
