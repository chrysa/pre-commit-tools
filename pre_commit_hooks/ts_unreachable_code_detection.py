#!/usr/bin/python3
"""Hook to detect unreachable code in TypeScript/TSX/JSX files using tree-sitter."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, int, str]

_TERMINAL_TYPES: frozenset[str] = frozenset({
    'return_statement',
    'throw_statement',
    'break_statement',
    'continue_statement',
})

# Node types whose direct named children are statement lists
_BLOCK_TYPES: frozenset[str] = frozenset({'statement_block'})

# Case-clause types inside switch bodies
_CASE_TYPES: frozenset[str] = frozenset({'switch_case', 'switch_default'})

_DISABLE_COMMENT = '// unreachable-code: disable'

# Suffixes that use the TSX parser to support JSX syntax
_TSX_SUFFIXES: frozenset[str] = frozenset({'.tsx', '.jsx'})


def _statements_of(node: object) -> list[object]:
    """Return the direct statement children of a block or case node."""
    node_type: str = node.type  # type: ignore[attr-defined]
    children: list[object] = node.children  # type: ignore[attr-defined]

    if node_type in _BLOCK_TYPES:
        return [c for c in children if c.is_named and c.type not in ('comment', 'ERROR')]  # type: ignore[attr-defined]

    if node_type in _CASE_TYPES:
        # Skip tokens up to and including ':' then collect named statement children
        past_colon = False
        stmts: list[object] = []
        for child in children:
            if not past_colon:
                if child.type == ':':  # type: ignore[attr-defined]
                    past_colon = True
                continue
            if child.is_named and child.type not in ('comment', 'ERROR'):  # type: ignore[attr-defined]
                stmts.append(child)
        return stmts

    return []


def _check_statements(
    stmts: list[object],
    filename: str,
    lines: list[str],
) -> list[Violation]:
    """Return violations for unreachable statements following a terminal node."""
    violations: list[Violation] = []
    for i, stmt in enumerate(stmts):
        if stmt.type in _TERMINAL_TYPES and i + 1 < len(stmts):  # type: ignore[attr-defined]
            next_stmt = stmts[i + 1]
            line_idx: int = next_stmt.start_point[0]  # type: ignore[attr-defined]
            src_line = lines[line_idx] if line_idx < len(lines) else ''
            if _DISABLE_COMMENT in src_line:
                break
            stmt_label = stmt.type.replace('_statement', '')  # type: ignore[attr-defined]
            violations.append((filename, line_idx + 1, f'unreachable code after {stmt_label}'))
            break  # report only the first dead statement per block
    return violations


def _walk(node: object, filename: str, lines: list[str]) -> list[Violation]:
    """Recursively walk the AST and collect unreachable-code violations."""
    violations: list[Violation] = []

    stmts = _statements_of(node)
    if stmts:
        violations.extend(_check_statements(stmts, filename, lines))

    for child in node.children:  # type: ignore[attr-defined]
        violations.extend(_walk(child, filename, lines))

    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect unreachable code in TypeScript/TSX/JSX files; return 1 if any violation is found."""
    try:
        import tree_sitter_typescript as _tsts
        from tree_sitter import Language, Parser
    except ImportError:
        print(  # print-detection: disable
            'tree-sitter and tree-sitter-typescript are required: '
            'pip install tree-sitter tree-sitter-typescript '
            '(or add them to additional_dependencies)',
        )
        return 1

    ts_language = Language(_tsts.language_typescript())
    tsx_language = Language(_tsts.language_tsx())  # also used for .jsx

    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='detect unreachable code in TypeScript/TSX/JSX files')
    args, _ = tools_instance.get_args(argv=argv)

    ret_val = 0
    for filename in args.filenames:
        path = Path(filename)
        try:
            source = path.read_text(encoding='utf-8')
        except OSError:
            continue
        lines = source.splitlines()
        lang = tsx_language if path.suffix.lower() in _TSX_SUFFIXES else ts_language
        parser = Parser(lang)
        tree = parser.parse(source.encode())
        for fname, lineno, msg in _walk(tree.root_node, filename, lines):
            print(f'[{fname}:{lineno}] {msg}')  # print-detection: disable
            ret_val = 1

    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
