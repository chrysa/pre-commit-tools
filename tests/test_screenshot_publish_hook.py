"""Tests for the screenshot-publish hook orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks import screenshot_publish
from pre_commit_hooks.screenshot_sync.manifest import Shot, write_manifest
from pre_commit_hooks.screenshot_sync.publish import notion


def _config(tmp_path: Path, body: str) -> None:
    (tmp_path / '.screenshot-sync.yaml').write_text(body, encoding='utf-8')


_README_ONLY = (
    'strategy: glob-url\n'
    'output_dir: docs/screenshots\n'
    'publish:\n'
    '  readme: {enabled: true, file: README.md, marker: screenshots}\n'
    '  notion: {enabled: false}\n'
)


class TestPublishHook:
    def test_no_config_returns_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert screenshot_publish.main([]) == 0

    def test_empty_manifest_returns_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _config(tmp_path, _README_ONLY)
        assert screenshot_publish.main([]) == 0

    def test_readme_updated_and_staged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _config(tmp_path, _README_ONLY)
        (tmp_path / 'README.md').write_text('# Project\n', encoding='utf-8')
        write_manifest(
            'docs/screenshots',
            [Shot(name='login', path='docs/screenshots/login.png', url='/login')],
        )
        staged: list[list[str]] = []
        monkeypatch.setattr(screenshot_publish, 'git_add', lambda paths: staged.append(paths))
        assert screenshot_publish.main([]) == 0
        assert '![login](docs/screenshots/login.png)' in (tmp_path / 'README.md').read_text()
        assert staged == [['README.md']]

    def test_notion_missing_key_skips_when_not_strict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _config(
            tmp_path,
            'strategy: glob-url\noutput_dir: docs/screenshots\n'
            'publish:\n'
            '  readme: {enabled: false}\n'
            '  notion: {enabled: true, page_id: p1}\n',
        )
        write_manifest('docs/screenshots', [Shot(name='a', path='a.png', url='/a')])
        monkeypatch.delenv('NOTION_API_KEY', raising=False)
        monkeypatch.setattr(screenshot_publish, 'git_add', lambda paths: None)
        assert screenshot_publish.main([]) == 0

    def test_notion_published_when_key_present(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _config(
            tmp_path,
            'strategy: glob-url\noutput_dir: docs/screenshots\n'
            'publish:\n'
            '  readme: {enabled: false}\n'
            '  notion: {enabled: true, page_id: p1, image_base_url: https://cdn/x}\n',
        )
        write_manifest('docs/screenshots', [Shot(name='a', path='a.png', url='/a')])
        monkeypatch.setenv('NOTION_API_KEY', 'tok')
        calls: dict[str, object] = {}
        monkeypatch.setattr(
            notion,
            'publish',
            lambda page_id, shots, token, image_base_url: calls.update({'page_id': page_id, 'token': token}),
        )
        assert screenshot_publish.main([]) == 0
        assert calls == {'page_id': 'p1', 'token': 'tok'}

    def test_notion_error_skips_when_not_strict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _config(
            tmp_path,
            'strategy: glob-url\noutput_dir: docs/screenshots\n'
            'publish:\n'
            '  readme: {enabled: false}\n'
            '  notion: {enabled: true, page_id: p1}\n',
        )
        write_manifest('docs/screenshots', [Shot(name='a', path='a.png', url='/a')])
        monkeypatch.setenv('NOTION_API_KEY', 'tok')

        def boom(page_id: str, shots: object, token: str, image_base_url: str) -> None:
            raise notion.NotionError('boom')

        monkeypatch.setattr(notion, 'publish', boom)
        assert screenshot_publish.main([]) == 0

    def test_readme_no_change_not_staged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _config(tmp_path, _README_ONLY)
        write_manifest('docs/screenshots', [Shot(name='a', path='a.png', url='/a')])
        monkeypatch.setattr(screenshot_publish, 'update_readme_file', lambda *a, **k: False)
        staged: list[list[str]] = []
        monkeypatch.setattr(screenshot_publish, 'git_add', lambda paths: staged.append(paths))
        assert screenshot_publish.main([]) == 0
        assert staged == []

    def test_malformed_config_does_not_block(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.screenshot-sync.yaml').write_text('strategy: bogus\n', encoding='utf-8')
        assert screenshot_publish.main([]) == 0
