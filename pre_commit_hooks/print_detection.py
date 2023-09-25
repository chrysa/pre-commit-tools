#!/usr/bin/python3
from __future__ import annotations

import logging
import re
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

PRINT_RE = re.compile(r'\bprint\(')
COMMENTED_RE = re.compile(r'\s#\s*print\(')
DISABLE_COMMENT_RE = re.compile(r'\bprint-detection\s*:\s*disable')

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def as_print(*, line):
    logger.debug(f'{line} | presence -> {bool(PRINT_RE.search(line))}')
    return bool(PRINT_RE.search(line))


def is_commented(*, line):
    logger.debug(f'{line} | commented -> {bool(COMMENTED_RE.search(line))}')
    return bool(COMMENTED_RE.search(line))


def is_disabked(*, line):
    logger.debug(f'{line} | disabled -> {bool(DISABLE_COMMENT_RE.search(line))}')
    return bool(DISABLE_COMMENT_RE.search(line))


def main(argv: Sequence[str] | None = None) -> int:
    tools_instance = PreCommitTools()
    args = tools_instance.set_params(help_msg='search print on python code', argv=argv)
    ret_val = 0
    for file in args.filenames:
        file = Path(file)
        with open(file) as stream:
            logging.debug(f'process file {file}')
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
