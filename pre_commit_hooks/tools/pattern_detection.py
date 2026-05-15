#!/usr/bin/python3
"""Shared detection engine used by pattern-based pre-commit hooks."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pre_commit_hooks.tools.logger import logger
from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


@dataclass
class PatternDetection:
    """Dataclass that holds compiled regex patterns and runs detection over files."""

    commented: re.Pattern[str]
    disable_comment: re.Pattern[str]
    pattern: re.Pattern[str]

    def as_pattern(self, *, line: str) -> bool:
        """Return True if the line matches the detection pattern."""
        logger.debug(f'{line} | presence -> {bool(self.pattern.search(line))}')
        return bool(self.pattern.search(line))

    def is_commented(self, *, line: str) -> bool:
        """Return True if the line is a commented-out occurrence of the pattern."""
        logger.debug(f'{line} | commented -> {bool(self.commented.search(line))}')
        return bool(self.commented.search(line))

    def is_disabled(self, *, line: str) -> bool:
        """Return True if the line contains an inline disable comment."""
        logger.debug(f'{line} | disabled -> {bool(self.disable_comment.search(line))}')
        return bool(self.disable_comment.search(line))

    def detect(self, *, argv: Sequence[str] | None = None) -> int:
        """Run detection across all files and return 1 if a violation is found."""
        tools_instance = PreCommitTools()
        tools_instance.set_params(help_msg='search print on python code')
        namespace_args, _ = tools_instance.get_args(
            argv=argv if argv is not None else [],
        )
        ret_val: int = 0
        for file in namespace_args.filenames:
            file_path = Path(file)
            with open(file_path) as stream:
                logger.debug(f'process file {file_path}')
                for line_number, line_content in enumerate(stream.readlines()):
                    if (
                        self.as_pattern(line=line_content)
                        and not self.is_disabled(line=line_content)
                        and not self.is_commented(line=line_content)
                    ):
                        print(
                            f'[{file_path}:{line_number}] {line_content.strip()}',
                        )  # print-detection: disable
                        ret_val = 1
        return ret_val
