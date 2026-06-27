"""Tests for the screenshot-capture hook orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks import screenshot_capture
from pre_commit_hooks.screenshot_sync.capture import runner
from pre_commit_hooks.screenshot_sync.manifest import Shot, read_manifest


def _write_config(tmp_path: Path, body: str) -> None:
    (tmp_path / '.screenshot-sync.yaml').write_text(body, encoding='utf-8')


_GLOB_CONFIG = (
    'strategy: glob-url\n'
    'base_url: http://localhost:5173\n'
    'output_dir: docs/screenshots\n'
    'routes:\n'
    '  - {match: "src/pages/Login.*", url: /login, name: login}\n'
)


class TestCaptureHook:
    def test_no_config_returns_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0

    def test_no_matching_target_returns_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)
        assert screenshot_capture.main(['src/util.ts']) == 0

    def test_happy_path_writes_manifest_and_stages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)
        monkeypatch.setattr(
            screenshot_capture,
            'capture_targets',
            lambda targets, out, vp: [
                Shot(name=t.name, path=f'docs/screenshots/{t.name}.png', url=t.url) for t in targets
            ],
        )
        staged: list[list[str]] = []
        monkeypatch.setattr(screenshot_capture, 'git_add', lambda paths: staged.append(paths))
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0
        shots = read_manifest('docs/screenshots')
        assert [s.name for s in shots] == ['login']
        assert staged == [['docs/screenshots']]

    def test_browser_unavailable_skips_when_not_strict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)

        def boom(targets: object, out: object, vp: object) -> list[Shot]:
            raise runner.BrowserUnavailableError('no browser')

        monkeypatch.setattr(screenshot_capture, 'capture_targets', boom)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0

    def test_capture_failed_skips_when_not_strict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG)

        def boom(targets: object, out: object, vp: object) -> list[Shot]:
            raise runner.CaptureFailedError('page unreachable')

        monkeypatch.setattr(screenshot_capture, 'capture_targets', boom)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 0

    def test_browser_unavailable_fails_when_strict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, _GLOB_CONFIG + 'strict: true\n')

        def boom(targets: object, out: object, vp: object) -> list[Shot]:
            raise runner.BrowserUnavailableError('no browser')

        monkeypatch.setattr(screenshot_capture, 'capture_targets', boom)
        assert screenshot_capture.main(['src/pages/Login.tsx']) == 1
