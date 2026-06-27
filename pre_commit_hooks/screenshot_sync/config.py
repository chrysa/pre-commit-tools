#!/usr/bin/python3
"""Load and validate the .screenshot-sync.yaml config file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_FILENAME = '.screenshot-sync.yaml'
_STRATEGIES = {'glob-url', 'storybook', 'fixed-routes'}


class ConfigError(ValueError):
    """Raised when the config file exists but is malformed or invalid."""


@dataclass
class Viewport:
    width: int = 1280
    height: int = 800


@dataclass
class Route:
    match: str
    url: str
    name: str


@dataclass
class FixedRoute:
    url: str
    name: str


@dataclass
class StoryEntry:
    match: str
    id: str
    name: str


@dataclass
class ReadmePublish:
    enabled: bool = True
    file: str = 'README.md'
    marker: str = 'screenshots'


@dataclass
class NotionPublish:
    enabled: bool = False
    page_id: str = ''
    image_base_url: str = ''


@dataclass
class PublishConfig:
    readme: ReadmePublish = field(default_factory=ReadmePublish)
    notion: NotionPublish = field(default_factory=NotionPublish)


@dataclass
class Config:
    strategy: str
    base_url: str
    output_dir: str
    viewport: Viewport
    strict: bool
    routes: list[Route]
    fixed_routes: list[FixedRoute]
    storybook_url: str
    stories: list[StoryEntry]
    publish: PublishConfig


def _as_dict(value: object, label: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f'{label} must be a mapping, got {type(value).__name__}')
    return value


def load_config(path: str | Path = CONFIG_FILENAME) -> Config | None:
    """Return the parsed Config, or None when the file does not exist."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f'invalid YAML in {path}: {exc}') from exc
    if not isinstance(raw, dict):
        raise ConfigError(f'{path} must contain a mapping at the top level')

    strategy = raw.get('strategy')
    if strategy not in _STRATEGIES:
        raise ConfigError(f'strategy must be one of {sorted(_STRATEGIES)}, got {strategy!r}')

    viewport_raw = _as_dict(raw.get('viewport'), 'viewport')
    try:
        viewport = Viewport(
            width=int(viewport_raw.get('width', 1280)),
            height=int(viewport_raw.get('height', 800)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f'invalid viewport in {path}: {exc}') from exc

    storybook_raw = _as_dict(raw.get('storybook'), 'storybook')
    try:
        routes = [Route(match=r['match'], url=r['url'], name=r['name']) for r in raw.get('routes', []) or []]
        fixed_routes = [FixedRoute(url=r['url'], name=r['name']) for r in raw.get('fixed_routes', []) or []]
        stories = [
            StoryEntry(match=s['match'], id=s['id'], name=s['name']) for s in storybook_raw.get('stories', []) or []
        ]
    except (KeyError, TypeError) as exc:
        raise ConfigError(f'invalid config in {path}: {exc}') from exc

    publish_raw = _as_dict(raw.get('publish'), 'publish')
    readme_raw = _as_dict(publish_raw.get('readme'), 'publish.readme')
    notion_raw = _as_dict(publish_raw.get('notion'), 'publish.notion')
    publish = PublishConfig(
        readme=ReadmePublish(
            enabled=bool(readme_raw.get('enabled', True)),
            file=str(readme_raw.get('file', 'README.md')),
            marker=str(readme_raw.get('marker', 'screenshots')),
        ),
        notion=NotionPublish(
            enabled=bool(notion_raw.get('enabled', False)),
            page_id=str(notion_raw.get('page_id', '')),
            image_base_url=str(notion_raw.get('image_base_url', '')),
        ),
    )

    return Config(
        strategy=strategy,
        base_url=str(raw.get('base_url', '')),
        output_dir=str(raw.get('output_dir', 'docs/screenshots')),
        viewport=viewport,
        strict=bool(raw.get('strict', False)),
        routes=routes,
        fixed_routes=fixed_routes,
        storybook_url=str(storybook_raw.get('url', '')),
        stories=stories,
        publish=publish,
    )
