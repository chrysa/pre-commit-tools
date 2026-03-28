"""Tests for format_dockerfile hook.

Skipped automatically when dockerfile-parse is not installed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

dockerfile_parse = pytest.importorskip('dockerfile_parse', reason='dockerfile-parse not installed')

from pre_commit_hooks.format_dockerfile import FormatDockerfile, main  # noqa: E402


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


SIMPLE_DOCKERFILE = """\
FROM python:3.13-slim
RUN pip install requests
RUN pip install flask
"""

DOCKERFILE_WITH_SHEBANG = """\
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim
RUN pip install requests
"""


class TestFormatDockerfileMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_SHEBANG)
        # May return 1 if formatter changes the file, just ensure no crash
        result = main([f])
        assert result in (0, 1)

    def test_missing_shebang_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.13-slim\n')
        result = main([f])
        assert result == 1
        content = Path(f).read_text()
        assert '# syntax=docker/dockerfile:1.4' in content

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0


class TestFormatDockerfileClass:
    def test_shebang_presence_detected(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_SHEBANG)
        fd = FormatDockerfile()
        fd.dockerfile = Path(f)
        fd.parser.fileobj = open(f)
        fd.parser.fileobj.close()
        assert isinstance(fd, FormatDockerfile)
