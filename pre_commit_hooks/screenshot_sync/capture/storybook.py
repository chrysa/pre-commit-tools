#!/usr/bin/python3
"""storybook strategy: map changed components to Storybook iframe URLs."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget, matches
from pre_commit_hooks.screenshot_sync.config import Config


def resolve_targets(config: Config, changed_files: list[str]) -> list[CaptureTarget]:
    base = config.storybook_url.rstrip('/')
    targets: list[CaptureTarget] = []
    for story in config.stories:
        if any(matches(path, story.match) for path in changed_files):
            ref = f'iframe.html?id={story.id}'
            targets.append(CaptureTarget(name=story.name, url=ref, full_url=f'{base}/{ref}'))
    return targets
