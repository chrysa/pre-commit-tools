#!/usr/bin/python3
from __future__ import annotations

import re
from pathlib import Path

from tools.pre_commit_tools import PreCommitTools

PRINT_RE = re.compile(r'\bprint\(')
COMMENTED_RE = re.compile(r'\s#\sprint\(')
DISABLE_COMMENT_RE = re.compile(r'\bprint-detection\s*:\s*disable')


def as_print(*, line):
    return bool(PRINT_RE.search(line))


def is_commented(*, line):
    return bool(COMMENTED_RE.search(line))


def is_disabked(*, line):
    return bool(DISABLE_COMMENT_RE.search(line))


def main(argve) -> int:
    tools_instance = PreCommitTools()
    args = tools_instance.set_params(help_msg='format dockerfile', argv=argv)
    ret_val = 0
    for file in args.filenames:
        file = Path(file)
        with open(file) as stream:
            for line_number, line_content in enumerate(stream.readlines()):
                if (
                    as_print(line=line_content)
                    and not is_disabked(line=line_content)
                    and not is_commented(line=line_content)
                ):
                    print(f'[{file}][L.{line_number}] {line_content}')  # print-detection: disable
                ret_val = 1
    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
