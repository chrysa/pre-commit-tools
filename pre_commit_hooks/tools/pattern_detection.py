#!/usr/bin/python3
"""Shared detection engine used by pattern-based pre-commit hooks."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pre_commit_hooks.tools.logger import logger
from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

_TRIPLE_QUOTE_RE = re.compile(r'"""|\'\'\'')


def strip_triple_quoted(*, line: str, open_quote: str | None) -> tuple[str, str | None]:
    """Drop triple-quoted text from a line, carrying the open delimiter across lines.

    Returns the code outside any triple-quoted string and the delimiter still
    open at end of line (None when the line ends outside a string).
    """
    code: list[str] = []
    position = 0
    for match in _TRIPLE_QUOTE_RE.finditer(line):
        delimiter = match.group(0)
        if open_quote is None:
            code.append(line[position : match.start()])
            open_quote = delimiter
        elif delimiter == open_quote:
            open_quote = None
        position = match.end()
    if open_quote is None:
        code.append(line[position:])
    return ''.join(code), open_quote


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

    def detect(self, *, argv: Sequence[str] | None = None, help_msg: str = 'detect pattern in files') -> int:
        """Run detection across all files and return 1 if a violation is found."""
        tools_instance = PreCommitTools()
        tools_instance.set_params(help_msg=help_msg)
        namespace_args, _ = tools_instance.get_args(argv=argv)
        ret_val: int = 0
        for file in namespace_args.filenames:
            file_path = Path(file)
            lines = file_path.read_bytes().decode('utf-8', errors='replace').splitlines(keepends=True)
            logger.debug(f'process file {file_path}')
            open_quote: str | None = None
            for line_number, line_content in enumerate(lines):
                code, open_quote = strip_triple_quoted(line=line_content, open_quote=open_quote)
                if (
                    self.as_pattern(line=code)
                    and not self.is_disabled(line=line_content)
                    and not self.is_commented(line=code)
                ):
                    print(
                        f'[{file_path}:{line_number}] {line_content.strip()}',
                    )  # print-detection: disable
                    ret_val = 1
        return ret_val
