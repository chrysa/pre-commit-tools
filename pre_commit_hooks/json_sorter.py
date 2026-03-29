#!/usr/bin/python3
"""Hook to sort JSON files keys alphabetically."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


def sort_json(data: Any) -> Any:
    """Sort a JSON object recursively (dicts by key, lists preserved)."""
    if isinstance(data, dict):
        return {k: sort_json(v) for k, v in sorted(data.items())}
    if isinstance(data, list):
        return [sort_json(item) for item in data]
    return data


def main(argv: Sequence[str] | None = None) -> int:
    """Sort JSON file keys alphabetically and return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='sort json file keys alphabetically')
    args, _ = tools_instance.get_args(argv=argv)
    changed_file_state = False
    for file in args.filenames:
        file = Path(file)
        with open(file) as file_stream:
            original = file_stream.read()
        data = json.loads(original)
        sorted_data = sort_json(data)
        new_content = json.dumps(sorted_data, indent=2, ensure_ascii=False) + '\n'
        if new_content != original:
            with open(file, mode='w') as file_stream:
                file_stream.write(new_content)
            changed_file_state = True
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
