#!/usr/bin/python3
"""Hook to validate the front matter of Claude Code skills (``SKILL.md``).

A skill is only discoverable when its ``SKILL.md`` opens with a YAML front matter
block declaring at least ``name`` and ``description``. Legacy skills written as a
plain ``# Skill: <title>`` heading carry no front matter and are therefore
invisible to the model even though the file looks correct to a human reviewer.

The hook fails on: a missing/unclosed/invalid front matter block, a missing
``name``/``description``, a ``name`` that is not kebab-case or does not match the
containing directory, and a ``description`` shorter than the minimum trigger
length. Unknown keys and an over-long description are reported as warnings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pre_commit_hooks.tools.frontmatter import check_required, check_unknown_keys, is_kebab_case, parse

ALLOWED_KEYS = frozenset(
    {
        'allowed-tools',
        'argument-hint',
        'description',
        'disable-model-invocation',
        'license',
        'metadata',
        'model',
        'name',
        'version',
    },
)
DEFAULT_MIN_DESCRIPTION = 20
DEFAULT_MAX_DESCRIPTION = 1024
LEGACY_HEADING = '# Skill:'
REQUIRED_KEYS = ('name', 'description')


def _legacy_hint(text: str) -> str:
    """Return an extra hint when the file uses the legacy ``# Skill:`` format."""
    if text.lstrip().startswith(LEGACY_HEADING):
        return " — legacy '# Skill:' format detected, migrate the title to a `name:` key"
    return ''


def _check_name(name: str, path: Path) -> list[str]:
    """Return errors for a skill ``name`` that is malformed or misplaced."""
    errors: list[str] = []
    if not is_kebab_case(name):
        errors.append(f'`name: {name}` must be lower-case kebab-case (e.g. `my-skill`)')
    directory = path.parent.name
    if directory and name != directory:
        errors.append(f'`name: {name}` must match the containing directory `{directory}/`')
    return errors


def _check_description(description: str, min_length: int, max_length: int) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the skill ``description`` trigger text."""
    errors: list[str] = []
    warnings: list[str] = []
    length = len(description.strip())
    if length < min_length:
        errors.append(
            f'`description` is {length} chars: too short to act as a trigger '
            f'(minimum {min_length}); state when the skill applies',
        )
    elif length > max_length:
        warnings.append(f'`description` is {length} chars, over the {max_length} recommended maximum')
    return errors, warnings


def check_skill(
    path: Path,
    min_description: int = DEFAULT_MIN_DESCRIPTION,
    max_description: int = DEFAULT_MAX_DESCRIPTION,
    extra_keys: frozenset[str] = frozenset(),
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one ``SKILL.md`` file."""
    text = path.read_text(encoding='utf-8', errors='replace')
    front = parse(text)
    if not front.found:
        return [f'no YAML front matter: the skill is invisible to Claude Code{_legacy_hint(text)}'], []
    if front.error is not None:
        return [front.error], []

    errors = check_required(front.data, REQUIRED_KEYS)
    warnings = check_unknown_keys(front.data, ALLOWED_KEYS | extra_keys)

    name = front.data.get('name')
    if isinstance(name, str) and name.strip():
        errors.extend(_check_name(name.strip(), path))

    description = front.data.get('description')
    if isinstance(description, str) and description.strip():
        desc_errors, desc_warnings = _check_description(description, min_description, max_description)
        errors.extend(desc_errors)
        warnings.extend(desc_warnings)
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    """Validate every ``SKILL.md`` passed on the command line."""
    parser = argparse.ArgumentParser(description='Validate Claude Code skill front matter')
    parser.add_argument('filenames', nargs='*', help='SKILL.md paths')
    parser.add_argument('--min-description', type=int, default=DEFAULT_MIN_DESCRIPTION)
    parser.add_argument('--max-description', type=int, default=DEFAULT_MAX_DESCRIPTION)
    parser.add_argument(
        '--allow-key',
        action='append',
        default=None,
        help='extra front matter key tolerated without warning (repeatable)',
    )
    args = parser.parse_args(argv)

    extra_keys = frozenset(args.allow_key or ())
    retval = 0
    for name in args.filenames:
        path = Path(name)
        if path.name != 'SKILL.md' or not path.exists():
            continue
        errors, warnings = check_skill(path, args.min_description, args.max_description, extra_keys)
        for warning in warnings:
            print(f'{path}: warning: {warning}', file=sys.stderr)
        for error in errors:
            print(f'{path}: error: {error}', file=sys.stderr)
        if errors:
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
