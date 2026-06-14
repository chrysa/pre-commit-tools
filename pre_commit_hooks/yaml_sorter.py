#!/usr/bin/python3
"""Hook to sort YAML mapping keys alphabetically.

Only mapping (dict) keys are sorted, recursively. YAML sequences (lists)
are ordered by the YAML spec and are always left in their original order:
reordering them corrupts order-sensitive YAML such as docker-compose
``healthcheck.test``, GitHub Actions ``steps`` and command argument lists.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from typing import Any

import yaml

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


def sort_yaml_file(
    changed_file_state: bool,
    data: dict[Any, Any],
    _initial_sorted: dict[Any, Any] | None = None,
) -> tuple[bool, dict[Any, Any]]:
    """Sort mapping keys recursively; sequences keep their original order."""
    sorted_data = dict(sorted(data.items(), key=lambda item: str(item[0])))
    changed_file_state |= list(sorted_data.keys()) != list(data.keys())
    for key, value in sorted_data.items():
        if isinstance(value, dict):
            sorted_data[key] = {}
            changed_file_state, sorted_data[key] = sort_yaml_file(
                changed_file_state,
                value,
            )
        elif isinstance(value, list):
            # YAML sequences are ordered by spec: never reorder them.
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
        with open(file) as file_stream:
            raw = yaml.safe_load(file_stream)
        if not isinstance(raw, dict):
            continue
        data = OrderedDict(raw)
        changed_file_state, sorted_data = sort_yaml_file(
            changed_file_state,
            data,
        )
        if changed_file_state:
            with open(file, mode='w') as file_stream:
                yaml.safe_dump(dict(sorted_data), file_stream, default_flow_style=False)
    return int(changed_file_state)


if __name__ == '__main__':
    raise SystemExit(main())
