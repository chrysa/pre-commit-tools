#!/usr/bin/python3
"""Inject a screenshots section into a README between HTML markers."""

from __future__ import annotations

import re
from pathlib import Path

from pre_commit_hooks.screenshot_sync.manifest import Shot


def render_section(shots: list[Shot]) -> str:
    """Return the markdown body: one image per shot."""
    return '\n'.join(f'![{shot.name}]({shot.path})' for shot in shots)


def inject(text: str, section: str, marker: str) -> str:
    """Replace content between the marker comments, creating them if absent."""
    start = f'<!-- {marker}:start -->'
    end = f'<!-- {marker}:end -->'
    block = f'{start}\n{section}\n{end}'
    pattern = re.compile(
        re.escape(start) + r'.*?' + re.escape(end),
        re.DOTALL,
    )
    if pattern.search(text):
        return pattern.sub(block, text)
    separator = '' if text.endswith('\n') or text == '' else '\n'
    return f'{text}{separator}\n{block}\n'


def update_readme_file(file: str | Path, shots: list[Shot], marker: str) -> bool:
    """Inject the rendered section into file; return True if content changed."""
    path = Path(file)
    original = path.read_text(encoding='utf-8') if path.exists() else ''
    updated = inject(original, render_section(shots), marker)
    if updated == original:
        return False
    path.write_text(updated, encoding='utf-8')
    return True
