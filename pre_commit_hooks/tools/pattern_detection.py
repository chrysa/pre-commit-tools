#!/usr/bin/python3
from __future__ import annotations

import logging
import typing
from dataclasses import dataclass
from pathlib import Path

from pre_commit_hooks.tools.logger import logger
from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

if typing.TYPE_CHECKING:
    import re

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


@dataclass
class PatternDetection:
    commented: re.Match[bytes]
    disable_comment: re.Match[bytes]
    pattern: re.Match[bytes]

    def as_pattern(self, *, line: str) -> bool:
        logger.debug(f'{line} | presence -> {bool(self.pattern.search(line))}')
        return bool(self.pattern.search(line))

    def is_commented(self, *, line: str) -> bool:
        logger.debug(f'{line} | commented -> {bool(self.commented.search(line))}')
        return bool(self.commented.search(line))

    def is_disabled(self, *, line: str) -> bool:
        logger.debug(f'{line} | disabled -> {bool(self.disable_comment.search(line))}')
        return bool(self.disable_comment.search(line))

    def detect(self, *, argv: Sequence[str] | None = None) -> int:
        tools_instance = PreCommitTools()
        tools_instance.set_params(help_msg='search print on python code')
        namespace_args, _ = tools_instance.get_args(argv=argv)
        ret_val = 0
        for file in namespace_args.filenames:
            file = Path(file)
            with open(file) as stream:
                logger.debug(f'process file {file}')
                for line_number, line_content in enumerate(stream.readlines()):
                    if (
                        self.as_pattern(line=line_content)
                        and not self.is_disabled(line=line_content)
                        and not self.is_commented(line=line_content)
                    ):
                        print(f'[{file}][L.{line_number}] {line_content.strip()}')  # print-detection: disable
                        ret_val = 1
        return ret_val
