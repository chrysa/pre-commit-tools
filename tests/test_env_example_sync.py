"""Tests for env_example_sync."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.env_example_sync import check_env_sync, main


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


class TestCheckEnvSync:
    def test_in_sync_returns_empty(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', 'FOO=bar\nBAZ=qux\n')
        _write(tmp_path / '.env.example', 'FOO=\nBAZ=\n')
        assert check_env_sync(tmp_path / '.env', tmp_path / '.env.example') == []

    def test_missing_key_in_example(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', 'FOO=bar\nSECRET=xyz\n')
        _write(tmp_path / '.env.example', 'FOO=\n')
        errors = check_env_sync(tmp_path / '.env', tmp_path / '.env.example')
        assert any('SECRET' in e for e in errors)

    def test_extra_key_in_example(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', 'FOO=bar\n')
        _write(tmp_path / '.env.example', 'FOO=\nEXTRA=\n')
        errors = check_env_sync(tmp_path / '.env', tmp_path / '.env.example')
        assert any('EXTRA' in e for e in errors)

    def test_missing_example_file(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', 'FOO=bar\n')
        errors = check_env_sync(tmp_path / '.env', tmp_path / '.env.example')
        assert len(errors) == 1
        assert 'missing' in errors[0]

    def test_no_env_file_no_error(self, tmp_path: Path) -> None:
        assert check_env_sync(tmp_path / '.env', tmp_path / '.env.example') == []

    def test_comments_ignored(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', '# this is a comment\nFOO=bar\n')
        _write(tmp_path / '.env.example', 'FOO=\n')
        assert check_env_sync(tmp_path / '.env', tmp_path / '.env.example') == []


class TestEnvExampleSyncMain:
    def test_in_sync_returns_0(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', 'A=1\nB=2\n')
        _write(tmp_path / '.env.example', 'A=\nB=\n')
        env = str(tmp_path / '.env')
        assert main([env, '--env-file', '.env', '--example-file', '.env.example']) == 0

    def test_out_of_sync_returns_1(self, tmp_path: Path) -> None:
        _write(tmp_path / '.env', 'A=1\nMISSING=secret\n')
        _write(tmp_path / '.env.example', 'A=\n')
        env = str(tmp_path / '.env')
        assert main([env, '--env-file', '.env', '--example-file', '.env.example']) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
