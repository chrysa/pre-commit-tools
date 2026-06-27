"""Tests for screenshot_sync.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.screenshot_sync.config import ConfigError, load_config


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / '.screenshot-sync.yaml'
    path.write_text(body, encoding='utf-8')
    return path


class TestLoadConfig:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert load_config(tmp_path / 'nope.yaml') is None

    def test_glob_url_minimal(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            'strategy: glob-url\n'
            'base_url: http://localhost:5173\n'
            'routes:\n'
            '  - {match: "src/pages/Login.*", url: /login, name: login}\n',
        )
        config = load_config(path)
        assert config is not None
        assert config.strategy == 'glob-url'
        assert config.base_url == 'http://localhost:5173'
        assert config.output_dir == 'docs/screenshots'
        assert config.strict is False
        assert config.viewport.width == 1280
        assert config.routes[0].url == '/login'
        assert config.routes[0].name == 'login'
        assert config.publish.readme.enabled is True
        assert config.publish.readme.marker == 'screenshots'
        assert config.publish.notion.enabled is False

    def test_fixed_routes_and_overrides(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            'strategy: fixed-routes\n'
            'base_url: http://localhost:3000\n'
            'output_dir: shots\n'
            'strict: true\n'
            'viewport: {width: 800, height: 600}\n'
            'fixed_routes:\n'
            '  - {url: /, name: home}\n'
            'publish:\n'
            '  readme: {enabled: false, file: docs/UI.md, marker: shots}\n'
            '  notion: {enabled: true, page_id: abc123, image_base_url: https://cdn/x}\n',
        )
        config = load_config(path)
        assert config is not None
        assert config.output_dir == 'shots'
        assert config.strict is True
        assert config.viewport.height == 600
        assert config.fixed_routes[0].name == 'home'
        assert config.publish.readme.enabled is False
        assert config.publish.readme.file == 'docs/UI.md'
        assert config.publish.notion.enabled is True
        assert config.publish.notion.page_id == 'abc123'
        assert config.publish.notion.image_base_url == 'https://cdn/x'

    def test_storybook_strategy(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            'strategy: storybook\n'
            'storybook:\n'
            '  url: http://localhost:6006\n'
            '  stories:\n'
            '    - {match: "src/Button.*", id: button--primary, name: button}\n',
        )
        config = load_config(path)
        assert config is not None
        assert config.storybook_url == 'http://localhost:6006'
        assert config.stories[0].id == 'button--primary'

    def test_unknown_strategy_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'strategy: magic\n')
        with pytest.raises(ConfigError):
            load_config(path)

    def test_missing_strategy_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'base_url: http://x\n')
        with pytest.raises(ConfigError):
            load_config(path)

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'strategy: [unclosed\n')
        with pytest.raises(ConfigError):
            load_config(path)
