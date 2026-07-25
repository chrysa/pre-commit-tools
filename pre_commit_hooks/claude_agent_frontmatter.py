#!/usr/bin/python3
"""Hook to validate the front matter of Claude Code subagents (``agents/*.md``).

A subagent definition is a Markdown file whose YAML front matter declares at
least ``name`` and ``description``; the body is the agent's system prompt. An
agent whose front matter is missing or malformed is never registered, so the
Agent tool silently cannot dispatch to it.

The hook fails on: a missing/unclosed/invalid front matter block, a missing
``name``/``description``, a ``name`` that is not kebab-case or does not match the
file stem, a ``tools`` value that is neither a list nor a comma-separated string,
and an empty prompt body. Unknown keys and an unrecognised ``model`` alias are
reported as warnings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from pre_commit_hooks.tools.frontmatter import check_required, check_unknown_keys, is_kebab_case, parse

ALLOWED_KEYS = frozenset({'color', 'description', 'isolation', 'model', 'name', 'tools'})
KNOWN_MODELS = frozenset({'fable', 'haiku', 'inherit', 'opus', 'sonnet'})
MODEL_ID_PREFIX = 'claude-'
REQUIRED_KEYS = ('name', 'description')


def _check_name(name: str, path: Path) -> list[str]:
    """Return errors for an agent ``name`` that is malformed or misplaced."""
    errors: list[str] = []
    if not is_kebab_case(name):
        errors.append(f'`name: {name}` must be lower-case kebab-case (e.g. `code-reviewer`)')
    if name != path.stem:
        errors.append(f'`name: {name}` must match the file name `{path.stem}.md`')
    return errors


def _check_tools(tools: Any) -> list[str]:
    """Return errors for a malformed ``tools`` declaration."""
    if isinstance(tools, str):
        if not tools.strip():
            return ['`tools` is empty: omit the key to inherit every tool']
        return []
    if isinstance(tools, list):
        if not tools:
            return ['`tools` is an empty list: omit the key to inherit every tool']
        bad = [item for item in tools if not isinstance(item, str) or not item.strip()]
        return ['`tools` list entries must be non-empty tool names'] if bad else []
    return ['`tools` must be a comma-separated string or a list of tool names']


def _check_model(model: Any) -> list[str]:
    """Return warnings for an unrecognised ``model`` value."""
    if not isinstance(model, str) or not model.strip():
        return ['`model` must be a model alias or id string']
    value = model.strip()
    if value in KNOWN_MODELS or value.startswith(MODEL_ID_PREFIX):
        return []
    return [f'`model: {value}` is neither a known alias ({", ".join(sorted(KNOWN_MODELS))}) nor a `claude-*` id']


def _has_body(text: str) -> bool:
    """Return True when content follows the closing front matter fence."""
    parts = text.lstrip().split('---', 2)
    return len(parts) == 3 and bool(parts[2].strip())


def check_agent(path: Path, extra_keys: frozenset[str] = frozenset()) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one subagent definition file."""
    text = path.read_text(encoding='utf-8', errors='replace')
    front = parse(text)
    if not front.found:
        return ['no YAML front matter: the subagent is never registered'], []
    if front.error is not None:
        return [front.error], []

    errors = check_required(front.data, REQUIRED_KEYS)
    warnings = check_unknown_keys(front.data, ALLOWED_KEYS | extra_keys)

    name = front.data.get('name')
    if isinstance(name, str) and name.strip():
        errors.extend(_check_name(name.strip(), path))
    if 'tools' in front.data:
        errors.extend(_check_tools(front.data['tools']))
    if 'model' in front.data:
        warnings.extend(_check_model(front.data['model']))
    if not _has_body(text):
        errors.append('empty body: the subagent has no system prompt')
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    """Validate every subagent definition passed on the command line."""
    parser = argparse.ArgumentParser(description='Validate Claude Code subagent front matter')
    parser.add_argument('filenames', nargs='*', help='agent definition paths')
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
        if not path.exists():
            continue
        errors, warnings = check_agent(path, extra_keys)
        for warning in warnings:
            print(f'{path}: warning: {warning}', file=sys.stderr)
        for error in errors:
            print(f'{path}: error: {error}', file=sys.stderr)
        if errors:
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
