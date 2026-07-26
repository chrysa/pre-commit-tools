#!/usr/bin/python3
"""Shared YAML front matter parsing for Claude Code asset hooks.

Claude Code discovers skills and subagents by reading a YAML front matter block
delimited by ``---`` fences at the very top of a Markdown file. A file without
that block is silently invisible to the model, so the parse result distinguishes
"no fence at all" from "fence present but broken".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

FENCE = '---'
NAME_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


@dataclass
class FrontMatter:
    """Outcome of parsing the front matter block of a Markdown asset file."""

    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    found: bool = False

    @property
    def usable(self) -> bool:
        """Return True when a block was found and parsed into a mapping."""
        return self.found and self.error is None


def is_kebab_case(value: str) -> bool:
    """Return True if *value* is lower-case kebab-case (``my-skill-name``)."""
    return bool(NAME_RE.fullmatch(value))


def _split_block(text: str) -> str | None:
    """Return the raw YAML block between the opening and closing fences."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FENCE:
            return '\n'.join(lines[1:index])
    return None


def parse(text: str) -> FrontMatter:
    """Parse the leading YAML front matter block of *text*."""
    if not text.lstrip().startswith(FENCE):
        return FrontMatter()

    block = _split_block(text)
    if block is None:
        return FrontMatter(found=True, error='front matter block is never closed by a `---` fence')

    import yaml

    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        message = str(exc).replace('\n', ' ')
        return FrontMatter(found=True, error=f'front matter is not valid YAML: {message}')

    if loaded is None:
        return FrontMatter(found=True, error='front matter block is empty')
    if not isinstance(loaded, dict):
        return FrontMatter(found=True, error='front matter must be a YAML mapping')
    return FrontMatter(data=loaded, found=True)


def check_required(data: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    """Return an error per required key that is missing or not a non-empty string."""
    errors: list[str] = []
    for key in required:
        value = data.get(key)
        if value is None:
            errors.append(f'missing required front matter key `{key}`')
        elif not isinstance(value, str) or not value.strip():
            errors.append(f'front matter key `{key}` must be a non-empty string')
    return errors


def check_unknown_keys(data: dict[str, Any], allowed: frozenset[str]) -> list[str]:
    """Return a warning per top-level key outside the documented schema."""
    unknown = sorted(key for key in data if key not in allowed)
    return [f'unknown front matter key `{key}` (ignored by Claude Code)' for key in unknown]
