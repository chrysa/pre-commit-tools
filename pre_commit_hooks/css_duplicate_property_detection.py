#!/usr/bin/python3
"""Hook to detect duplicate/overridden CSS property declarations and duplicate ID selectors."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

# (filename, duplicate_lineno, first_lineno, property_name)
Violation = tuple[str, int, int, str]

_BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)
_PROPERTY_RE = re.compile(r'^([\w-]+)\s*:')
_DISABLE_PROPERTY_COMMENT = '/* css-duplicate-property: disable */'
_DISABLE_ID_COMMENT = '/* css-duplicate-id: disable */'

# Lines that are selectors/at-rules, not property declarations
_NOT_PROPERTY_RE = re.compile(
    r'^\s*(@|&|\.|\#|::|:|>|\*|\[|--|from\b|to\b|\d)',
)

# Matches #id-name in a selector line (outside property context)
_ID_SELECTOR_RE = re.compile(r'#([a-zA-Z][\w-]*)')


def _strip_block_comments(content: str) -> str:
    """Replace block comment content with spaces, preserving line numbers."""

    def _sub(m: re.Match[str]) -> str:
        return '\n' * m.group(0).count('\n')

    return _BLOCK_COMMENT.sub(_sub, content)


def detect_duplicate_properties(content: str, filename: str) -> list[Violation]:
    """Return violations for duplicate CSS property declarations within the same rule block."""
    original_lines = content.splitlines()  # keep for disable-comment lookup
    stripped_content = _strip_block_comments(content)
    lines = stripped_content.splitlines()
    violations: list[Violation] = []

    # Stack of dicts: each dict maps property_name → first_lineno for one nesting level
    scope_stack: list[dict[str, int]] = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped or stripped.startswith('//'):
            continue

        # Update nesting for opening braces
        open_count = stripped.count('{')
        close_count = stripped.count('}')

        for _ in range(open_count):
            scope_stack.append({})

        # Detect property: value pattern (before processing closing braces)
        if scope_stack and ':' in stripped:
            if not _NOT_PROPERTY_RE.match(stripped) and not stripped.endswith('{') and not stripped.endswith(','):
                m = _PROPERTY_RE.match(stripped)
                if m:
                    prop = m.group(1).lower()
                    if _DISABLE_PROPERTY_COMMENT not in original_lines[lineno - 1]:
                        current_scope = scope_stack[-1]
                        if prop in current_scope:
                            violations.append((filename, lineno, current_scope[prop], prop))
                        else:
                            current_scope[prop] = lineno

        # Update nesting for closing braces
        for _ in range(close_count):
            if scope_stack:
                scope_stack.pop()

    return violations


# (filename, duplicate_lineno, first_lineno, id_name)
IdViolation = tuple[str, int, int, str]


def detect_duplicate_ids(content: str, filename: str) -> list[IdViolation]:
    """Return violations for CSS ID selectors that appear in more than one rule block.

    An ID selector (#foo) should only be used once in a stylesheet since IDs must be
    unique in the DOM.  Using the same ID selector in multiple rule blocks indicates
    either poor specificity design or a copy-paste error.
    """
    original_lines = content.splitlines()
    stripped_content = _strip_block_comments(content)
    lines = stripped_content.splitlines()
    violations: list[IdViolation] = []

    # Track: id_name → first_lineno (only selector lines, not property lines)
    seen_ids: dict[str, int] = {}
    depth = 0

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        open_count = stripped.count('{')
        close_count = stripped.count('}')

        # Selector lines: depth == 0 before the opening brace and contain '{'
        if open_count and depth == 0:
            if _DISABLE_ID_COMMENT not in original_lines[lineno - 1]:
                for id_name in _ID_SELECTOR_RE.findall(stripped):
                    id_lower = id_name.lower()
                    if id_lower in seen_ids:
                        violations.append((filename, lineno, seen_ids[id_lower], id_name))
                    else:
                        seen_ids[id_lower] = lineno

        depth += open_count - close_count

    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect duplicate CSS properties and duplicate ID selectors; return 1 if any violation is found."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='detect duplicate/overridden properties and duplicate ID selectors in CSS files')
    args, _ = tools_instance.get_args(argv=argv)
    ret_val = 0
    for filename in args.filenames:
        path = Path(filename)
        try:
            content = path.read_text(encoding='utf-8')
        except OSError:
            continue
        for fname, lineno, first_lineno, prop in detect_duplicate_properties(content, filename):
            print(  # print-detection: disable
                f'[{fname}:{lineno}] duplicate property "{prop}" (first declared at line {first_lineno})',
            )
            ret_val = 1
        for fname, lineno, first_lineno, id_name in detect_duplicate_ids(content, filename):
            print(  # print-detection: disable
                f'[{fname}:{lineno}] duplicate ID selector "#{id_name}" (first used at line {first_lineno})',
            )
            ret_val = 1
    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
