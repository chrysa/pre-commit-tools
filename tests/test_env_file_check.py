"""Tests for env_file_check."""
from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.env_file_check import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestEnvFileCheck:
    @pytest.mark.parametrize('key', [
        'PASSWORD', 'SECRET', 'TOKEN', 'API_KEY', 'PRIVATE_KEY',
        'CLIENT_SECRET', 'AUTH_KEY', 'ACCESS_KEY',
    ])
    def test_real_secret_returns_1(self, tmp_path: Path, key: str) -> None:
        f = _write(tmp_path, '.env', f'{key}=supersecretvalue\n')
        assert main([f]) == 1

    @pytest.mark.parametrize('value', [
        '<your-token>', '${TOKEN}', 'changeme', 'example', 'dummy', 'fake',
        'none', 'null', 'false', 'true', '0', '',
    ])
    def test_placeholder_returns_0(self, tmp_path: Path, value: str) -> None:
        f = _write(tmp_path, '.env', f'PASSWORD={value}\n')
        assert main([f]) == 0

    def test_comment_line_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '.env', '# PASSWORD=secret\n')
        assert main([f]) == 0

    def test_blank_line_ignored(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '.env', '\nPASSWORD=\n')
        assert main([f]) == 0

    def test_unrelated_key_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '.env', 'APP_NAME=myapp\n')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
