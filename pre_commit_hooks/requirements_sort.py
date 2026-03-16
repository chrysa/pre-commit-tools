#!/usr/bin/python3
"""Hook to sort requirements files alphabetically."""
from __future__ import annotations

import typing
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

if typing.TYPE_CHECKING:
    from collections.abc import Sequence


def sort_requirements(lines: list[str]) -> list[str]:
    """Sort requirements lines: comments/blanks first, packages sorted case-insensitively."""
    comments = [line for line in lines if not line.strip() or line.strip().startswith('#')]
    packages = [line for line in lines if line.strip() and not line.strip().startswith('#')]
    sorted_packages = sorted(packages, key=lambda x: x.split('#')[0].strip().lower())
    return comments + sorted_packages


def main(argv: Sequence[str] | None = None) -> int:
    """Sort requirements file alphabetically and return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='sort requirements file alphabetically')
    args, _ = tools_instance.get_args(argv=argv)
    changed_file_state = False
    for file in args.filenames:
        file = Path(file)
        with open(file) as file_stream:
            lines = file_stream.readlines()
        sorted_lines = sort_requirements([line.rstrip('\n') for line in lines])
        new_content = '\n'.join(sorted_lines) + '\n'
        original = ''.join(lines)
        if new_content != original:
            with open(file, mode='w') as file_stream:
                file_stream.write(new_content)
            changed_file_state = True
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
