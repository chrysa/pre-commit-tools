"""Tests for screenshot_sync.manifest."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.screenshot_sync.manifest import (
    Shot,
    manifest_path,
    read_manifest,
    write_manifest,
)


class TestManifest:
    def test_read_missing_returns_empty(self, tmp_path: Path) -> None:
        assert read_manifest(tmp_path / 'shots') == []

    def test_write_then_read_roundtrip(self, tmp_path: Path) -> None:
        out = tmp_path / 'shots'
        shots = [
            Shot(name='login', path='shots/login.png', url='/login'),
            Shot(name='home', path='shots/home.png', url='/'),
        ]
        returned = write_manifest(out, shots)
        assert returned == manifest_path(out)
        assert returned.exists()
        assert read_manifest(out) == shots

    def test_write_creates_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / 'nested' / 'shots'
        write_manifest(out, [Shot(name='a', path='a.png', url='/a')])
        assert out.is_dir()
