#!/usr/bin/python3
"""Hook to sort YAML files keys alphabetically."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from typing import Any

import yaml

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


def sort_yaml_file(
    changed_file_state: bool,
    data: dict[Any, Any],
    sorted_data: dict[Any, Any],
) -> tuple[bool, dict[Any, Any]]:
    """Sort a YAML dict recursively; return updated change flag and sorted dict."""
    sorted_data = dict(sorted(data.items(), key=lambda item: str(item[0])))
    changed_file_state |= list(sorted_data.keys()) != list(data.keys())
    for key, value in sorted_data.items():
        if isinstance(value, dict):
            sorted_data[key] = {}
            changed_file_state, sorted_data[key] = sort_yaml_file(changed_file_state, value, sorted_data[key])
        elif isinstance(value, list):
            if all(not isinstance(item, (dict, list)) for item in value):
                sorted_data[key] = sorted(value)
                changed_file_state |= sorted_data[key] != value
            else:
                sorted_data[key] = value
        else:
            sorted_data[key] = value
    return changed_file_state, sorted_data


def main(argv: Sequence[str] | None = None) -> int:  # noqa: C901
    """Sort YAML file keys alphabetically and return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='sort yaml file')
    args, _ = tools_instance.get_args(argv=argv)
    changed_file_state = False
    for file in args.filenames:
        sorted_data = OrderedDict()
        with open(file) as file_stream:
            raw = yaml.safe_load(file_stream)
        if not isinstance(raw, dict):
            continue
        data = OrderedDict(raw)
        changed_file_state, sorted_data = sort_yaml_file(changed_file_state, data, sorted_data)
        if changed_file_state:
            with open(file, mode='w') as file_stream:
                yaml.safe_dump(dict(sorted_data), file_stream, default_flow_style=False)
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
