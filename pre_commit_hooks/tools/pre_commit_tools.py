#!/usr/bin/python3
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path


class PreCommitTools:
    args: argparse.Namespace

    def set_params(self, *, help_msg: str, argv: Sequence[str] | None = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        parser.add_argument('filenames', nargs='*', help=help_msg)
        parser.add_argument('--force', action='store_true')
        self.args = parser.parse_args(argv)
        return self.args

    def file_exist(self, *, file: Path, display: bool = True) -> bool:
        retval: bool = True
        if not file.exists():
            if display:
                print(f'{file}: not exist')
            retval = False
        return retval

    def file_empty(self, *, file: Path, display: bool = True) -> bool:
        retval: bool = False
        if self.file_exist(file=file, display=display):
            if not file.stat().st_size:
                if display:
                    print(f'{file}: is empty')
                retval = True
        else:
            retval = True
        return retval
