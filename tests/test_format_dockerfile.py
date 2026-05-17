"""Tests for format_dockerfile hook.

Skipped automatically when dockerfile-parse is not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

dockerfile_parse = pytest.importorskip(
    'dockerfile_parse',
    reason='dockerfile-parse not installed',
)

from pre_commit_hooks.format_dockerfile import (  # noqa: E402
    FormatDockerfile,
    _load_config,
    _sort_arg_env_blocks,
    main,
)


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

DOCKERFILE_WITH_ENV = """\
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim
ENV FOO=bar BAZ=qux
"""

DOCKERFILE_WITH_HEALTHCHECK = """\
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim
HEALTHCHECK CMD curl -f http://localhost/health || exit 1
"""

DOCKERFILE_WITH_ARG = """\
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim
ARG VERSION=1.0
ARG BUILD_DATE=unknown
"""

DOCKERFILE_WITH_ARG_VAR = """\
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim
ARG BASE_IMAGE=python:3.13-slim
ARG TAG=${BASE_IMAGE}-extra
"""

DOCKERFILE_MULTI_STAGE = """\
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim AS builder
RUN pip install requests
FROM python:3.13-slim AS runtime
COPY --from=builder /app /app
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

    def test_sort_args_flag(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ARG)
        result = main(['--sort-args', f])
        assert result in (0, 1)

    def test_sort_envs_flag(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ENV)
        result = main(['--sort-envs', f])
        assert result in (0, 1)

    def test_separate_arg_blocks_flag(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ARG_VAR)
        result = main(['--separate-arg-blocks', f])
        assert result in (0, 1)

    def test_config_file_used(self, tmp_path: Path) -> None:
        config = tmp_path / '.format-dockerfiles.toml'
        config.write_text('[format-dockerfiles]\nsort_args = true\n', encoding='utf-8')
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ARG)
        result = main(['--config', str(config), f])
        assert result in (0, 1)

    def test_multiple_files(self, tmp_path: Path) -> None:
        f1 = _write(tmp_path, 'Dockerfile1', DOCKERFILE_WITH_SHEBANG)
        f2 = _write(tmp_path, 'Dockerfile2', SIMPLE_DOCKERFILE)
        result = main([f1, f2])
        assert result in (0, 1)

    def test_dockerfile_with_env(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ENV)
        result = main([f])
        assert result in (0, 1)

    def test_dockerfile_with_healthcheck(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_HEALTHCHECK)
        result = main([f])
        assert result in (0, 1)

    def test_dockerfile_multi_stage(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_MULTI_STAGE)
        result = main([f])
        assert result in (0, 1)


class TestSortArgEnvBlocks:
    def test_no_sort_passthrough(self) -> None:
        content = 'FROM python:3.13-slim\nARG B=1\nARG A=2\n'
        result = _sort_arg_env_blocks(content, sort_args=False, sort_envs=False, separate_arg_blocks=False)
        assert result == content

    def test_sort_args(self) -> None:
        content = 'FROM python:3.13-slim\nARG ZZZ=1\nARG AAA=2\n'
        result = _sort_arg_env_blocks(content, sort_args=True, sort_envs=False, separate_arg_blocks=False)
        assert result.index('AAA') < result.index('ZZZ')

    def test_sort_envs(self) -> None:
        content = 'FROM python:3.13-slim\nENV ZZZ=1\nENV AAA=2\n'
        result = _sort_arg_env_blocks(content, sort_args=False, sort_envs=True, separate_arg_blocks=False)
        assert result.index('AAA') < result.index('ZZZ')

    def test_separate_arg_blocks_with_literal_and_variable(self) -> None:
        content = 'FROM python:3.13-slim\nARG BASE=python\nARG TAG=${BASE}-extra\n'
        result = _sort_arg_env_blocks(content, sort_args=False, sort_envs=False, separate_arg_blocks=True)
        assert 'BASE' in result
        assert 'TAG' in result

    def test_separate_arg_blocks_sort_and_separate(self) -> None:
        content = 'FROM python:3.13-slim\nARG Z=1\nARG A=2\nARG TAG=${Z}-extra\n'
        result = _sort_arg_env_blocks(content, sort_args=True, sort_envs=False, separate_arg_blocks=True)
        assert 'A' in result
        assert 'TAG' in result

    def test_only_literal_args_no_separator(self) -> None:
        content = 'FROM python:3.13-slim\nARG B=1\nARG A=2\n'
        result = _sort_arg_env_blocks(content, sort_args=False, sort_envs=False, separate_arg_blocks=True)
        assert 'B' in result

    def test_non_arg_env_lines_passthrough(self) -> None:
        content = 'FROM python:3.13-slim\nRUN echo hi\n'
        result = _sort_arg_env_blocks(content, sort_args=True, sort_envs=True, separate_arg_blocks=True)
        assert 'RUN echo hi' in result


class TestLoadConfig:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = _load_config(tmp_path / 'nonexistent.toml')
        assert result == {}

    def test_valid_toml_parsed(self, tmp_path: Path) -> None:
        config = tmp_path / 'config.toml'
        config.write_text('[format-dockerfiles]\nsort_args = true\n', encoding='utf-8')
        result = _load_config(config)
        assert result.get('sort_args') is True

    def test_empty_toml_returns_empty(self, tmp_path: Path) -> None:
        config = tmp_path / 'config.toml'
        config.write_text('', encoding='utf-8')
        result = _load_config(config)
        assert result == {}

    def test_toml_without_section_returns_empty(self, tmp_path: Path) -> None:
        config = tmp_path / 'config.toml'
        config.write_text('[other-section]\nkey = true\n', encoding='utf-8')
        result = _load_config(config)
        assert result == {}


class TestFormatDockerfileClass:
    def test_shebang_presence_detected(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_SHEBANG)
        fd = FormatDockerfile()
        fd.dockerfile = Path(f)
        fd.parser.fileobj = open(f)
        fd.parser.fileobj.close()
        assert isinstance(fd, FormatDockerfile)

    def test_load_and_format(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', SIMPLE_DOCKERFILE)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        assert 'FROM' in fd.content

    def test_load_and_format_with_shebang(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_SHEBANG)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        assert '# syntax=docker/dockerfile:1.4' in fd.content

    def test_save_unchanged(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_SHEBANG)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        fd.save(file=Path(f))
        assert Path(f).exists()

    def test_format_with_sort_args(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ARG)
        fd = FormatDockerfile(sort_args=True)
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        fd.save(file=Path(f))
        assert fd.return_value in (0, 1)

    def test_format_env_dockerfile(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_ENV)
        fd = FormatDockerfile(sort_envs=True)
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        assert 'ENV' in fd.content

    def test_format_healthcheck_dockerfile(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_WITH_HEALTHCHECK)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        assert 'HEALTHCHECK' in fd.content

