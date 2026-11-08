"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run from tmp_path: path-guarded hooks only read files under the working tree."""
    monkeypatch.chdir(tmp_path)
    return tmp_path
