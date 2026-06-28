#!/usr/bin/python3
"""Hook to detect Docker Compose services missing `restart: unless-stopped`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import yaml


def main(argv: Sequence[str] | None = None) -> int:
    """Return 1 if any compose service lacks restart: unless-stopped."""
    parser = argparse.ArgumentParser(description='Detect compose services missing restart policy.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        try:
            data = yaml.safe_load(Path(filename).read_text(encoding='utf-8'))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        services = data.get('services')
        if not isinstance(services, dict):
            continue
        for name, spec in services.items():
            if not isinstance(spec, dict) or spec.get('restart') != 'unless-stopped':
                msg = f'[{filename}] service "{name}" must set restart: unless-stopped'
                print(msg)  # print-detection: disable
                ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
