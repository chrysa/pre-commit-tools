#!/usr/bin/python3
"""Hook to sort YAML files keys alphabetically."""
from __future__ import annotations

import typing
from collections import OrderedDict

import yaml

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

if typing.TYPE_CHECKING:
    from collections.abc import Sequence


def sort_yaml_file(changed_file_state: bool, data: dict, sorted_data: dict) -> tuple[bool, dict]:
    """Sort a YAML dict recursively; return updated change flag and sorted dict."""
    sorted_data = dict(sorted(data.items()))
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


def main(argv: Sequence[str] | None = None) -> int:
    """Sort YAML file keys alphabetically and return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='sort yaml file')
    args, _ = tools_instance.get_args(argv=argv)
    changed_file_state = False
    for file in args.filenames:
        sorted_data = OrderedDict()
        with open(file) as file_stream:
            data = OrderedDict(yaml.safe_load(file_stream))
            changed_file_state, sorted_data = sort_yaml_file(changed_file_state, data, sorted_data)
        if changed_file_state:
            with open(file, mode='w') as file_stream:
                yaml.safe_dump(dict(sorted_data), file_stream, default_flow_style=False)
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
