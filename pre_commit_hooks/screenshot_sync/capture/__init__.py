"""Capture target resolution: dispatch on the configured strategy."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture import (
    fixed_routes,
    glob_url,
    storybook,
)
from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Config

_STRATEGIES = {
    'glob-url': glob_url.resolve_targets,
    'fixed-routes': fixed_routes.resolve_targets,
    'storybook': storybook.resolve_targets,
}


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    """Resolve capture targets for the configured strategy, de-duped by name."""
    resolver = _STRATEGIES[config.strategy]
    seen: set[str] = set()
    unique: list[CaptureTarget] = []
    for target in resolver(config, changed_files):
        if target.name not in seen:
            seen.add(target.name)
            unique.append(target)
    return unique
