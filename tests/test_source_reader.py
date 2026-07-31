"""Tests for the tools.source_reader helper."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.tools.source_reader import read_source


class TestReadSource:
    def test_file_inside_root_is_read(self, tmp_path: Path) -> None:
        target = tmp_path / 'mod.py'
        target.write_text('x = 1\n', encoding='utf-8')
        assert read_source(str(target), root=tmp_path) == 'x = 1\n'

    def test_nested_file_inside_root_is_read(self, tmp_path: Path) -> None:
        nested = tmp_path / 'pkg' / 'sub'
        nested.mkdir(parents=True)
        target = nested / 'mod.py'
        target.write_text('y = 2\n', encoding='utf-8')
        assert read_source(str(target), root=tmp_path) == 'y = 2\n'

    def test_path_escaping_root_returns_none(self, tmp_path: Path) -> None:
        outside = tmp_path / 'outside.py'
        outside.write_text('secret = 1\n', encoding='utf-8')
        root = tmp_path / 'project'
        root.mkdir()
        assert read_source(str(root / '..' / 'outside.py'), root=root) is None

    def test_absolute_path_outside_root_returns_none(self, tmp_path: Path) -> None:
        root = tmp_path / 'project'
        root.mkdir()
        assert read_source('/etc/hostname', root=root) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert read_source(str(tmp_path / 'absent.py'), root=tmp_path) is None

    def test_non_utf8_file_returns_none(self, tmp_path: Path) -> None:
        target = tmp_path / 'bin.py'
        target.write_bytes(b'\xff\xfe\x00binary')
        assert read_source(str(target), root=tmp_path) is None

    def test_root_defaults_to_cwd(self, tmp_path: Path, monkeypatch) -> None:
        target = tmp_path / 'mod.py'
        target.write_text('z = 3\n', encoding='utf-8')
        monkeypatch.chdir(tmp_path)
        assert read_source('mod.py') == 'z = 3\n'
