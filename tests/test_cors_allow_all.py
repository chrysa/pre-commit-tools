"""Tests for cors_allow_all."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.cors_allow_all import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestCorsAllowAll:
    def test_fastapi_wildcard_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'app.add_middleware(CORSMiddleware, allow_origins=["*"])\n')]) == 1

    def test_django_allow_all_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'CORS_ALLOW_ALL_ORIGINS = True\n')]) == 1

    def test_explicit_origins_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'allow_origins=["https://app.example.com"]\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'allow_origins=["*"]  # cors-allow-all: disable\n')]) == 0

    def test_commented_line_skipped(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '# allow_origins=["*"]\n')]) == 0
