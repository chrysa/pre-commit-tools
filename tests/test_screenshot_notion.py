"""Tests for screenshot_sync.publish.notion (requests mocked)."""

from __future__ import annotations

import pytest

from pre_commit_hooks.screenshot_sync.manifest import Shot
from pre_commit_hooks.screenshot_sync.publish import notion

_SHOTS = [Shot(name='login', path='docs/screenshots/login.png', url='/login')]


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.text = 'error-body'


class TestBuildBlocks:
    def test_external_image_when_base_url(self) -> None:
        blocks = notion.build_blocks(_SHOTS, 'https://cdn.example/repo')
        assert blocks[0]['type'] == 'image'
        assert blocks[0]['image']['external']['url'] == 'https://cdn.example/repo/docs/screenshots/login.png'

    def test_paragraph_fallback_without_base_url(self) -> None:
        blocks = notion.build_blocks(_SHOTS, '')
        assert blocks[0]['type'] == 'paragraph'
        text = blocks[0]['paragraph']['rich_text'][0]['text']['content']
        assert 'login' in text


class TestPublish:
    def test_posts_to_children_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake_patch(url: str, *, headers: dict, json: dict, timeout: float) -> _FakeResponse:
            captured['url'] = url
            captured['headers'] = headers
            captured['json'] = json
            return _FakeResponse(200)

        monkeypatch.setattr(notion.requests, 'patch', fake_patch)
        notion.publish('page123', _SHOTS, 'secret-token', 'https://cdn/x')
        assert captured['url'] == 'https://api.notion.com/v1/blocks/page123/children'
        assert captured['headers']['Authorization'] == 'Bearer secret-token'
        assert 'Notion-Version' in captured['headers']
        assert captured['json']['children'][0]['type'] == 'image'

    def test_non_2xx_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(notion.requests, 'patch', lambda *a, **k: _FakeResponse(401))
        with pytest.raises(notion.NotionError):
            notion.publish('page123', _SHOTS, 'bad', '')
