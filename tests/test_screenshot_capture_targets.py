"""Tests for screenshot_sync.capture target resolution."""

from __future__ import annotations

from pre_commit_hooks.screenshot_sync.capture import resolve_targets
from pre_commit_hooks.screenshot_sync.capture.targets import matches
from pre_commit_hooks.screenshot_sync.config import (
    Config,
    FixedRoute,
    PublishConfig,
    Route,
    StoryEntry,
    Viewport,
)


def _config(**overrides: object) -> Config:
    base: dict[str, object] = {
        'strategy': 'glob-url',
        'base_url': 'http://localhost:5173',
        'output_dir': 'docs/screenshots',
        'viewport': Viewport(),
        'strict': False,
        'routes': [],
        'fixed_routes': [],
        'storybook_url': 'http://localhost:6006',
        'stories': [],
        'publish': PublishConfig(),
    }
    base.update(overrides)
    return Config(**base)


class TestMatches:
    def test_full_path_glob(self) -> None:
        assert matches('src/pages/Login.tsx', 'src/pages/Login.*') is True

    def test_basename_glob(self) -> None:
        assert matches('deep/nested/Login.tsx', 'Login.*') is True

    def test_no_match(self) -> None:
        assert matches('src/util.ts', 'src/pages/Login.*') is False


class TestGlobUrl:
    def test_changed_file_maps_to_route(self) -> None:
        config = _config(
            routes=[Route(match='src/pages/Login.*', url='/login', name='login')],
        )
        targets = resolve_targets(config, ['src/pages/Login.tsx'])
        assert len(targets) == 1
        assert targets[0].name == 'login'
        assert targets[0].url == '/login'
        assert targets[0].full_url == 'http://localhost:5173/login'

    def test_unmatched_file_yields_nothing(self) -> None:
        config = _config(
            routes=[Route(match='src/pages/Login.*', url='/login', name='login')],
        )
        assert resolve_targets(config, ['src/util.ts']) == []

    def test_dedup_by_name(self) -> None:
        config = _config(
            routes=[Route(match='src/pages/Login.*', url='/login', name='login')],
        )
        targets = resolve_targets(config, ['src/pages/Login.tsx', 'src/pages/Login.css'])
        assert len(targets) == 1


class TestFixedRoutes:
    def test_any_change_captures_all(self) -> None:
        config = _config(
            strategy='fixed-routes',
            base_url='http://localhost:3000',
            fixed_routes=[FixedRoute(url='/', name='home'), FixedRoute(url='/about', name='about')],
        )
        targets = resolve_targets(config, ['src/anything.tsx'])
        assert [t.name for t in targets] == ['home', 'about']
        assert targets[0].full_url == 'http://localhost:3000/'

    def test_no_changes_yields_nothing(self) -> None:
        config = _config(
            strategy='fixed-routes',
            fixed_routes=[FixedRoute(url='/', name='home')],
        )
        assert resolve_targets(config, []) == []


class TestStorybook:
    def test_changed_component_maps_to_story(self) -> None:
        config = _config(
            strategy='storybook',
            stories=[StoryEntry(match='src/Button.*', id='comp-button--primary', name='button')],
        )
        targets = resolve_targets(config, ['src/Button.tsx'])
        assert len(targets) == 1
        assert targets[0].name == 'button'
        assert targets[0].url == 'iframe.html?id=comp-button--primary'
        assert targets[0].full_url == 'http://localhost:6006/iframe.html?id=comp-button--primary'
