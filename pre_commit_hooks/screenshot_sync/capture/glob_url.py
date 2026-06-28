#!/usr/bin/python3
"""glob-url strategy: map changed files to base_url + route."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget, matches
from pre_commit_hooks.screenshot_sync.config import Config


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    base = config.base_url.rstrip('/')
    targets: list[CaptureTarget] = []
    for route in config.routes:
        if any(matches(path, route.match) for path in changed_files):
            targets.append(
                CaptureTarget(
                    name=route.name,
                    url=route.url,
                    full_url=f'{base}{route.url}',
                ),
            )
    return targets
