#!/usr/bin/python3
"""Hook to sort Makefile rules alphabetically by target name."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


def _target_name(line: str) -> str | None:
    """Return the primary target of a rule line, or None if the line is not a rule.

    A rule line is ``target [target...]: [prerequisites]``. Variable assignments
    (``:=``, ``::=``, ``?=``, ``+=``, ``=``, ``!=``), recipe lines (leading tab),
    comments, blank lines and special targets (``.PHONY`` and friends) are ignored.
    """
    if not line or line[0] in ' \t#':
        return None
    colon = line.find(':')
    # Not a rule: no colon, or the colon opens an assignment (:=, ::=).
    if colon == -1 or line[colon + 1 : colon + 2] == '=' or line[colon + 1 : colon + 3] == ':=':
        return None
    head = line[:colon]
    if '=' in head:  # assignment operator (?=, +=, !=, =) before any colon
        return None
    targets = head.split()
    if not targets:
        return None
    name = targets[0]
    if name.startswith('.'):  # special target (.PHONY, .DEFAULT...) — keep pinned
        return None
    return name


def _is_continued(line: str) -> bool:
    """Return True if the line continues onto the next one (trailing backslash)."""
    return line.rstrip().endswith('\\')


class _Chunk:
    """A contiguous group of Makefile lines, either a rule block or anything else."""

    def __init__(self, lines: list[str], key: str | None = None) -> None:
        self.lines = lines
        self.key = key  # target name for rule chunks, None otherwise


def _parse_chunks(lines: list[str]) -> list[_Chunk]:
    """Split Makefile lines into rule chunks and non-rule chunks.

    A rule chunk gathers its leading adjacent comment lines, the target line
    (with prerequisite continuations) and the tab-indented recipe, so it can be
    reordered as a self-contained block. Blank lines stay as pinned separators.
    """
    chunks: list[_Chunk] = []
    comment_buffer: list[str] = []
    index = 0
    total = len(lines)

    def flush_comments() -> None:
        if comment_buffer:
            chunks.append(_Chunk(comment_buffer.copy()))
            comment_buffer.clear()

    while index < total:
        line = lines[index]
        # A `define NAME ... endef` multiline variable: its body lines may look
        # like rules (``name: ...``) but must never be parsed or reordered as
        # such. Pin the whole block as one non-rule chunk.
        if line.lstrip().split(' ', 1)[0] == 'define':
            flush_comments()
            block = [line]
            index += 1
            while index < total and lines[index].strip() != 'endef':
                block.append(lines[index])
                index += 1
            if index < total:  # the `endef` line itself
                block.append(lines[index])
                index += 1
            chunks.append(_Chunk(block))
            continue
        name = _target_name(line)
        if line.startswith('#'):
            comment_buffer.append(line)
            index += 1
            continue
        if name is not None:
            block = [*comment_buffer, line]
            comment_buffer.clear()
            index += 1
            # prerequisite line continuations
            while index < total and _is_continued(block[-1]):
                block.append(lines[index])
                index += 1
            # recipe lines (tab-indented, with their own continuations)
            while index < total and lines[index].startswith('\t'):
                block.append(lines[index])
                index += 1
                while index < total and _is_continued(block[-1]):
                    block.append(lines[index])
                    index += 1
            chunks.append(_Chunk(block, key=name))
            continue
        # any other line (blank, variable, include, unattached comment run)
        flush_comments()
        if chunks and chunks[-1].key is None:
            chunks[-1].lines.append(line)
        else:
            chunks.append(_Chunk([line]))
        index += 1

    flush_comments()
    return chunks


# Conditional/define directives that scope which rules `make` sees. Rules must
# never be reordered across them, or a rule can silently move into/out of a
# conditional and change what gets built.
_BARRIER_PREFIXES = ('ifeq', 'ifneq', 'ifdef', 'ifndef', 'else', 'endif', 'define', 'endef')


def _is_barrier(chunk: _Chunk) -> bool:
    """True if a non-rule chunk carries a conditional/define directive."""
    if chunk.key is not None:
        return False
    return any(line.lstrip().split(' ', 1)[0] in _BARRIER_PREFIXES for line in chunk.lines)


def sort_makefile(content: str) -> str:
    """Return content with its make rules sorted alphabetically by target name.

    Non-rule content (preamble, variables, ``.PHONY`` declarations, includes) keeps
    its position; rule blocks are reordered within the slots they occupy, but never
    across a conditional (``ifeq``/``else``/``endif``) or ``define`` boundary — so a
    rule cannot be moved into or out of a conditional block.
    """
    trailing_newline = content.endswith('\n')
    lines = content.split('\n')
    if trailing_newline:
        lines.pop()

    chunks = _parse_chunks(lines)
    # Sort rule slots independently within each run delimited by barrier chunks.
    groups: list[list[int]] = []
    current: list[int] = []
    for i, chunk in enumerate(chunks):
        if _is_barrier(chunk):
            if current:
                groups.append(current)
                current = []
        elif chunk.key is not None:
            current.append(i)
    if current:
        groups.append(current)

    for positions in groups:
        sorted_rules = sorted(
            (chunks[i] for i in positions),
            key=lambda chunk: (str(chunk.key).lower(), str(chunk.key)),
        )
        for position, target_index in enumerate(positions):
            chunks[target_index] = sorted_rules[position]

    out_lines: list[str] = []
    for chunk in chunks:
        out_lines.extend(chunk.lines)
    result = '\n'.join(out_lines)
    if trailing_newline:
        result += '\n'
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Sort Makefile rules alphabetically and return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='sort makefile rules alphabetically')
    args, _ = tools_instance.get_args(argv=argv)
    changed_file_state = False
    for filename in args.filenames:
        file = Path(filename)
        original = file.read_text(encoding='utf-8')
        new_content = sort_makefile(original)
        if new_content != original:
            file.write_text(new_content, encoding='utf-8')
            changed_file_state = True
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
