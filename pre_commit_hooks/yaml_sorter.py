#!/usr/bin/python3
from collections import OrderedDict
from pathlib import Path

import yaml
from tools.pre_commit_tools import PreCommitTools


def sort_yaml_file(changed_file_state, data, sorted_data):
    sorted_data = dict(sorted(data.items()))
    changed_file_state = list(sorted_data.keys()) != list(data.keys())
    for key, value in sorted_data.items():
        if isinstance(value, dict):
            sorted_data[key] = {}
            changed_file_state, sorted_data[key] = sort_yaml_file(changed_file_state, value, sorted_data[key])
        elif isinstance(value, list):
            sorted_data[key] = sorted(value)
            changed_file_state = sorted_data[key] != value
        else:
            sorted_data[key] = value
            if isinstance(value, dict):
                changed_file_state = list(sorted_data[key].keys()) != list(value)
            else:
                changed_file_state = sorted_data[key] == value
    return changed_file_state, sorted_data


def main(argv=None):
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
            with open(file, mode="w") as file_stream:
                yaml.safe_dump(dict(sorted_data), file_stream, default_flow_style=False)
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
