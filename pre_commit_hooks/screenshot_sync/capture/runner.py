#!/usr/bin/python3
"""Render capture targets to PNG files with Playwright."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Viewport
from pre_commit_hooks.screenshot_sync.manifest import Shot

try:  # Playwright is an optional, heavy dependency.
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised via monkeypatch in tests
    sync_playwright = None


class BrowserUnavailableError(RuntimeError):
    """Raised when Playwright or its browser binary is not installed."""


class CaptureFailedError(RuntimeError):
    """Raised when a page cannot be loaded or screenshotted."""


def capture_targets(
    targets: list[CaptureTarget],
    output_dir: str | Path,
    viewport: Viewport,
) -> list[Shot]:
    """Screenshot every target; return one Shot per captured target."""
    if sync_playwright is None:
        raise BrowserUnavailableError('playwright is not installed')

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    shots: list[Shot] = []
    try:
        with sync_playwright() as play:
            browser = play.chromium.launch()
            try:
                page = browser.new_page()
                page.set_viewport_size({'width': viewport.width, 'height': viewport.height})
                for target in targets:
                    png = out / f'{target.name}.png'
                    try:
                        page.goto(target.full_url, wait_until='networkidle', timeout=15000)
                        page.screenshot(path=str(png), full_page=True)
                    except Exception as exc:
                        raise CaptureFailedError(f'failed to capture {target.full_url}: {exc}') from exc
                    shots.append(Shot(name=target.name, path=str(png), url=target.url))
            finally:
                browser.close()
    except CaptureFailedError:
        raise
    except Exception as exc:
        raise BrowserUnavailableError(f'cannot launch browser: {exc}') from exc
    return shots
