#!/usr/bin/python3
"""Hook to publish captured screenshots to the README and/or Notion."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from pre_commit_hooks.screenshot_sync.config import load_config
from pre_commit_hooks.screenshot_sync.gitutil import git_add
from pre_commit_hooks.screenshot_sync.manifest import read_manifest
from pre_commit_hooks.screenshot_sync.publish import notion
from pre_commit_hooks.screenshot_sync.publish.readme import update_readme_file
from pre_commit_hooks.screenshot_sync.reporting import skip_or_fail


def main(argv: Sequence[str] | None = None) -> int:
    """Publish the manifest's screenshots to the configured destinations."""
    parser = argparse.ArgumentParser(description='Publish captured screenshots.')
    parser.add_argument('filenames', nargs='*', help='Ignored (pass_filenames: false).')
    parser.parse_args(argv)

    config = load_config()
    if config is None:
        return 0

    shots = read_manifest(config.output_dir)
    if not shots:
        return 0

    if config.publish.readme.enabled:
        readme_cfg = config.publish.readme
        if update_readme_file(readme_cfg.file, shots, readme_cfg.marker):
            git_add([readme_cfg.file])

    if config.publish.notion.enabled:
        notion_cfg = config.publish.notion
        token = os.environ.get('NOTION_API_KEY')
        if not token:
            return skip_or_fail(config.strict, 'NOTION_API_KEY is not set; skipping Notion')
        try:
            notion.publish(notion_cfg.page_id, shots, token, notion_cfg.image_base_url)
        except notion.NotionError as exc:
            return skip_or_fail(config.strict, str(exc))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
