#!/usr/bin/python3
"""fixed-routes strategy: capture every configured route when any file changed."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Config


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    if not changed_files:
        return []
    base = config.base_url.rstrip('/')
    return [
        CaptureTarget(name=route.name, url=route.url, full_url=f'{base}{route.url}') for route in config.fixed_routes
    ]
