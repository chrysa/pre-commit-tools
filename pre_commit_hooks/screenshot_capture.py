#!/usr/bin/python3
"""Hook to screenshot UI screens affected by staged files."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from pre_commit_hooks.screenshot_sync.capture import resolve_targets
from pre_commit_hooks.screenshot_sync.capture.runner import (
    BrowserUnavailableError,
    CaptureFailedError,
    capture_targets,
)
from pre_commit_hooks.screenshot_sync.config import ConfigError, load_config
from pre_commit_hooks.screenshot_sync.gitutil import git_add
from pre_commit_hooks.screenshot_sync.manifest import write_manifest
from pre_commit_hooks.screenshot_sync.reporting import skip_or_fail


def main(argv: Sequence[str] | None = None) -> int:
    """Capture screenshots for changed UI files and stage them."""
    parser = argparse.ArgumentParser(description='Screenshot UI screens for a commit.')
    parser.add_argument('filenames', nargs='*', help='Staged files (from pre-commit).')
    args = parser.parse_args(argv)

    try:
        config = load_config()
    except ConfigError as exc:
        return skip_or_fail(False, f'invalid .screenshot-sync.yaml: {exc}')
    if config is None:
        return 0

    targets = resolve_targets(config, list(args.filenames))
    if not targets:
        return 0

    try:
        shots = capture_targets(targets, config.output_dir, config.viewport)
    except (BrowserUnavailableError, CaptureFailedError) as exc:
        return skip_or_fail(config.strict, str(exc))

    write_manifest(config.output_dir, shots)
    git_add([config.output_dir])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
