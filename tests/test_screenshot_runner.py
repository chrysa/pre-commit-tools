"""Tests for screenshot_sync.capture.runner (Playwright mocked)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.screenshot_sync.capture import runner
from pre_commit_hooks.screenshot_sync.capture.targets import CaptureTarget
from pre_commit_hooks.screenshot_sync.config import Viewport


class _FakePage:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self._rec = recorder

    def set_viewport_size(self, size: dict[str, int]) -> None:
        self._rec.append(('viewport', size))

    def goto(self, url: str, wait_until: str = 'load', timeout: float = 0) -> None:
        self._rec.append(('goto', url))

    def screenshot(self, path: str, full_page: bool = True) -> None:
        self._rec.append(('screenshot', path))
        Path(path).write_bytes(b'PNG')


class _FakeBrowser:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self._rec = recorder

    def new_page(self) -> _FakePage:
        return _FakePage(self._rec)

    def close(self) -> None:
        self._rec.append(('close', None))


class _FakeChromium:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self._rec = recorder

    def launch(self) -> _FakeBrowser:
        return _FakeBrowser(self._rec)


class _FakePlaywrightCtx:
    def __init__(self, recorder: list[tuple[str, object]]) -> None:
        self.chromium = _FakeChromium(recorder)

    def __enter__(self) -> _FakePlaywrightCtx:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _fake_sync_playwright(recorder: list[tuple[str, object]]):
    def factory() -> _FakePlaywrightCtx:
        return _FakePlaywrightCtx(recorder)

    return factory


class TestCaptureTargets:
    def test_writes_png_and_returns_shots(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        recorder: list[tuple[str, object]] = []
        monkeypatch.setattr(runner, 'sync_playwright', _fake_sync_playwright(recorder))
        out = tmp_path / 'shots'
        targets = [CaptureTarget(name='home', url='/', full_url='http://x/')]
        shots = runner.capture_targets(targets, out, Viewport(width=800, height=600))
        assert len(shots) == 1
        assert shots[0].name == 'home'
        assert shots[0].url == '/'
        assert Path(shots[0].path).exists()
        assert ('goto', 'http://x/') in recorder
        assert ('viewport', {'width': 800, 'height': 600}) in recorder

    def test_missing_playwright_raises_browser_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(runner, 'sync_playwright', None)
        with pytest.raises(runner.BrowserUnavailableError):
            runner.capture_targets(
                [CaptureTarget(name='a', url='/a', full_url='http://x/a')],
                'shots',
                Viewport(),
            )
