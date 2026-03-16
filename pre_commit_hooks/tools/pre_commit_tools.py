#!/usr/bin/python3
"""Base class providing shared argument parsing and file utilities for hooks."""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path


class PreCommitTools:
    """Shared base class for all pre-commit hooks."""

    args: argparse.Namespace
    parser: argparse.ArgumentParser()

    def file_exist(self, *, file: Path, display: bool = True) -> bool:
        """Return True if the file exists, printing a message if not and display is True."""
        retval: bool = True
        if not file.exists():
            if display:
                print(f'{file}: not exist')
            retval = False
        return retval

    def file_empty(self, *, file: Path, display: bool = True) -> bool:
        """Return True if the file is empty or does not exist."""
        retval: bool = False
        if self.file_exist(file=file, display=display):
            if not file.stat().st_size:
                if display:
                    print(f'{file}: is empty')
                retval = True
        else:
            retval = True
        return retval

    def get_args(self, *, argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, list]:
        """Parse and return known arguments from argv."""
        return self.parser.parse_known_args(argv)

    def set_params(self, *, help_msg: str, arguments: list[tuple[str, dict]] = None) -> None:
        """Configure the argument parser with optional extra arguments."""
        self.parser = argparse.ArgumentParser()
        if arguments is not None:
            for arg in arguments:
                self.parser.add_argument(arg[0], **arg[1])
        self.parser.add_argument('filenames', nargs='*', help=help_msg)
