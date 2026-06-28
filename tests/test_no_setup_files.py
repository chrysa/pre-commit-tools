"""Tests for no_setup_files."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_setup_files import main


def _write(tmp_path: Path, name: str, body: str = '') -> str:
    p = tmp_path / name
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestNoSetupFiles:
    def test_setup_py_always_flagged(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.py', 'from setuptools import setup\n')]) == 1

    def test_setup_cfg_with_metadata_flagged(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.cfg', '[metadata]\nname = x\n')]) == 1

    def test_setup_cfg_with_options_flagged(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.cfg', '[options]\npackages = find:\n')]) == 1

    def test_setup_cfg_uwsgi_style_allowed(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'setup.cfg', '[uwsgi]\nsocket = :9000\n')]) == 0

    def test_unrelated_file_returns_0(self, tmp_path: Path) -> None:
        assert main([_write(tmp_path, 'pyproject.toml', '[project]\n')]) == 0
