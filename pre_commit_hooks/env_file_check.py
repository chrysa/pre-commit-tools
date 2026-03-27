#!/usr/bin/python3
"""Hook to detect potential secrets committed in .env files."""
from __future__ import annotations

import re
import typing
from pathlib import Path

from pre_commit_hooks.tools.logger import logger
from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

_SECRET_KEY_RE = re.compile(
    r'^(PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|APIKEY|PRIVATE_KEY|AUTH_KEY|ACCESS_KEY|CREDENTIAL|CREDENTIALS'
    r'|CLIENT_SECRET|OAUTH_SECRET|ENCRYPTION_KEY|SIGNING_KEY|MASTER_KEY)\s*=\s*(.+)$',
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(
    r'^$|^<.+>$|^\$\{.+\}$|^%.+%$'
    r'|^(?:your[-_]|change[-_]?me|todo|fixme|example|test|dummy|fake|none|null|false|true|0)$',
    re.IGNORECASE,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Check .env files for committed secrets and return 1 if any are found."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='check .env files for committed secrets')
    args, _ = tools_instance.get_args(argv=argv)
    ret_val = 0
    for file in args.filenames:
        file = Path(file)
        logger.debug(f'process file {file}')
        with open(file) as file_stream:
            for line_number, line_content in enumerate(file_stream.readlines()):
                line_content = line_content.rstrip('\n')
                if not line_content.strip() or line_content.strip().startswith('#'):
                    continue
                match = _SECRET_KEY_RE.match(line_content)
                if match:
                    value = match.group(2).strip().strip('"').strip("'")
                    if not _PLACEHOLDER_RE.match(value):
                        print(
                            f'[{file}][L.{line_number}] potential secret committed: {match.group(1)}',
                        )  # print-detection: disable
                        ret_val = 1
    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
