#!/usr/bin/python3
"""Append screenshot blocks to a Notion page via the REST API."""

from __future__ import annotations

import requests

from pre_commit_hooks.screenshot_sync.manifest import Shot

_API_VERSION = '2022-06-28'


class NotionError(RuntimeError):
    """Raised when the Notion API call fails."""


def build_blocks(shots: list[Shot], image_base_url: str) -> list[dict]:
    """Build Notion block payloads for the shots."""
    base = image_base_url.rstrip('/')
    blocks: list[dict] = []
    for shot in shots:
        if base:
            blocks.append(
                {
                    'object': 'block',
                    'type': 'image',
                    'image': {
                        'type': 'external',
                        'external': {'url': f'{base}/{shot.path}'},
                    },
                }
            )
        else:
            blocks.append(
                {
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': f'{shot.name}: {shot.path}'},
                            }
                        ]
                    },
                }
            )
    return blocks


def publish(page_id: str, shots: list[Shot], token: str, image_base_url: str) -> None:
    """Append the shots as blocks to the given Notion page."""
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': _API_VERSION,
        'Content-Type': 'application/json',
    }
    payload = {'children': build_blocks(shots, image_base_url)}
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise NotionError(f'Notion request failed: {exc}') from exc
    if not 200 <= response.status_code < 300:
        raise NotionError(f'Notion API returned {response.status_code}: {response.text}')
