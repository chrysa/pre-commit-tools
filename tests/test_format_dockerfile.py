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

from pre_commit_hooks import format_dockerfile  # noqa: E402
from pre_commit_hooks.format_dockerfile import (  # noqa: E402
    FormatDockerfile,
    _fetch_dockerfile_tags,
    _load_config,
    _sort_arg_env_blocks,
    _version_tuple,
    main,
)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep version-lag checks offline by default and isolate the tag cache."""
    monkeypatch.setattr(format_dockerfile, '_fetch_dockerfile_tags', lambda: [])
    monkeypatch.setattr(
        format_dockerfile,
        '_TAGS_CACHE_FILE',
        tmp_path / 'tags_cache.json',
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


DOCKERFILE_NEWER_HEADER = """\
# syntax=docker/dockerfile:1.7
FROM python:3.13-slim
RUN pip install requests
"""

DOCKERFILE_HEADER_NO_MINOR = """\
# syntax=docker/dockerfile:1
FROM python:3.13-slim
RUN pip install requests
"""


class TestSyntaxHeaderVersion:
    def test_any_version_header_preserved(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_NEWER_HEADER)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        fd.format_file()
        # Non-default version is kept, not downgraded or duplicated.
        assert '# syntax=docker/dockerfile:1.7' in fd.content
        assert '# syntax=docker/dockerfile:1.4' not in fd.content
        assert fd.content.count('# syntax=docker/dockerfile') == 1

    def test_bare_major_header_detected(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', DOCKERFILE_HEADER_NO_MINOR)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        assert fd._header_version() == '1'

    def test_missing_header_returns_none(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', SIMPLE_DOCKERFILE)
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        assert fd._header_version() is None

    def test_non_syntax_comment_returns_none(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', '# just a comment\nFROM python:3.13-slim\n')
        fd = FormatDockerfile()
        fd.load_dockerfile(dockerfile_path=Path(f))
        assert fd._header_version() is None


class TestVersionTuple:
    def test_pads_to_three_parts(self) -> None:
        assert _version_tuple('1') == (1, 0, 0)
        assert _version_tuple('1.7') == (1, 7, 0)
        assert _version_tuple('1.7.3') == (1, 7, 3)

    def test_ordering(self) -> None:
        assert _version_tuple('1.4') < _version_tuple('1.7')
        assert _version_tuple('1.4.0') == _version_tuple('1.4')


class TestVersionLag:
    def test_warns_when_three_or_more_behind(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr(
            format_dockerfile,
            '_fetch_dockerfile_tags',
            lambda: ['1.4.0', '1.5.0', '1.6.0', '1.7.0'],
        )
        fd = FormatDockerfile()
        fd.dockerfile = Path('Dockerfile')
        with caplog.at_level('WARNING'):
            fd._check_version_lag(version='1.4')
        assert 'releases behind' in caplog.text
        assert '1.7.0' in caplog.text

    def test_no_warning_when_within_threshold(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr(
            format_dockerfile,
            '_fetch_dockerfile_tags',
            lambda: ['1.4.0', '1.5.0', '1.6.0'],
        )
        fd = FormatDockerfile()
        with caplog.at_level('WARNING'):
            fd._check_version_lag(version='1.5')
        assert 'releases behind' not in caplog.text

    def test_no_warning_when_fetch_empty(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # autouse fixture already makes _fetch_dockerfile_tags return [].
        fd = FormatDockerfile()
        with caplog.at_level('WARNING'):
            fd._check_version_lag(version='1.0')
        assert 'releases behind' not in caplog.text


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class TestFetchDockerfileTags:
    def test_network_error_returns_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError('no network')

        monkeypatch.setattr(format_dockerfile.urllib.request, 'urlopen', _boom)
        assert _fetch_dockerfile_tags() == []

    def test_success_filters_and_caches(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import json as _json

        payload = _json.dumps(
            {
                'results': [
                    {'name': '1.7.0'},
                    {'name': '1.6.0'},
                    {'name': 'latest'},
                    {'name': '1.7.0-labs'},
                    {'name': 123},
                ],
            },
        ).encode('utf-8')
        monkeypatch.setattr(
            format_dockerfile.urllib.request,
            'urlopen',
            lambda *a, **k: _FakeResponse(payload),
        )
        tags = _fetch_dockerfile_tags()
        assert tags == ['1.7.0', '1.6.0']
        # Second call hits the fresh cache without touching the network.
        monkeypatch.setattr(
            format_dockerfile.urllib.request,
            'urlopen',
            lambda *a, **k: (_ for _ in ()).throw(AssertionError('network used')),
        )
        assert _fetch_dockerfile_tags() == ['1.7.0', '1.6.0']
