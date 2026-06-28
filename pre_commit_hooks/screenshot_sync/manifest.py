#!/usr/bin/python3
"""Read and write the screenshot manifest shared by capture and publish."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

MANIFEST_FILENAME = '.screenshot-manifest.json'


@dataclass
class Shot:
    name: str
    path: str
    url: str


def manifest_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / MANIFEST_FILENAME


def write_manifest(output_dir: str | Path, shots: list[Shot]) -> Path:
    """Write the manifest under output_dir, creating the directory if needed."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = manifest_path(out)
    payload = {'shots': [asdict(shot) for shot in shots]}
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return path


def read_manifest(output_dir: str | Path) -> list[Shot]:
    """Return the manifest's shots, or an empty list when it does not exist."""
    path = manifest_path(output_dir)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return [Shot(**entry) for entry in data.get('shots', [])]
