#!/usr/bin/python3
"""Hook to sort the entries of ignore files (.gitignore, .dockerignore, …).

By default, entries are sorted alphabetically (case-insensitive) within each
contiguous run of pattern lines. Comment lines and blank lines act as fixed
anchors: they keep their position, so section headers and their grouping are
preserved. A leading ``!`` is ignored when computing the sort key, keeping a
negation pattern adjacent to the pattern it whitelists.

Alternatively, ``--sort-script PATH`` delegates ordering to a custom script:
the script receives the whole file content on stdin and the filename as its
first argument, and must print the sorted content to stdout.
"""

from __future__ import annotations

import subprocess  # nosec
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


def sort_ignore_lines(lines: list[str]) -> list[str]:
    """Sort ignore entries alphabetically within each contiguous pattern run.

    Blank and comment lines are anchors kept exactly in place; only the
    pattern lines between two anchors are reordered among themselves.
    """
    result: list[str] = []
    run: list[str] = []

    def flush() -> None:
        run.sort(key=_sort_key)
        result.extend(run)
        run.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            flush()
            result.append(line)
        else:
            run.append(line)
    flush()
    return result


def _sort_key(line: str) -> str:
    """Case-insensitive sort key ignoring a leading ``!`` negation marker."""
    return line.strip().removeprefix('!').lower()


def _run_sort_script(*, script: str, filename: str, content: str) -> str:
    """Delegate ordering to a user-provided script via stdin/stdout."""
    completed = subprocess.run(
        [script, filename],
        input=content,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def main(argv: Sequence[str] | None = None) -> int:
    """Sort ignore files in-place; return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(
        help_msg='sort ignore files alphabetically',
        arguments=[
            (
                '--sort-script',
                {
                    'default': None,
                    'help': 'path to a custom sort script; it receives the file '
                    'content on stdin and the filename as argv[1], and must '
                    'print the sorted content to stdout',
                },
            ),
        ],
    )
    args, _ = tools_instance.get_args(argv=argv)
    changed = False
    for file in args.filenames:
        path = Path(file)
        original = path.read_text(encoding='utf-8')
        if args.sort_script:
            new_content = _run_sort_script(script=args.sort_script, filename=file, content=original)
        else:
            new_content = '\n'.join(sort_ignore_lines(original.splitlines()))
            if original.endswith('\n'):
                new_content += '\n'
        if new_content != original:
            path.write_text(new_content, encoding='utf-8')
            changed = True
    return int(changed)


if __name__ == '__main__':
    raise SystemExit(main())
