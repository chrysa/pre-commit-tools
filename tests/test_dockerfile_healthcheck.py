"""Tests for dockerfile_healthcheck."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.dockerfile_healthcheck import detect_missing_healthcheck, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectMissingHealthcheck:
    def test_healthcheck_present_ok(self) -> None:
        src = (
            'FROM python:3.12 AS builder\n'
            'RUN pip install app\n'
            'FROM python:3.12-slim\n'
            'COPY --from=builder /app /app\n'
            'HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1\n'
        )
        assert detect_missing_healthcheck(src, 'Dockerfile') == []

    def test_missing_healthcheck_detected(self) -> None:
        src = 'FROM python:3.12-slim\nRUN pip install app\n'
        violations = detect_missing_healthcheck(src, 'Dockerfile')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'HEALTHCHECK' in msg

    def test_healthcheck_in_builder_stage_not_final(self) -> None:
        src = (
            'FROM python:3.12 AS builder\n'
            'HEALTHCHECK CMD curl -f http://localhost/health || exit 1\n'
            'FROM python:3.12-slim\n'
            'COPY --from=builder /app /app\n'
        )
        violations = detect_missing_healthcheck(src, 'Dockerfile')
        assert len(violations) == 1

    def test_disable_comment_suppresses(self) -> None:
        src = '# dockerfile-healthcheck: disable\nFROM python:3.12-slim\n'
        assert detect_missing_healthcheck(src, 'Dockerfile') == []

    def test_empty_dockerfile_no_violation(self) -> None:
        src = '# just a comment\n'
        assert detect_missing_healthcheck(src, 'Dockerfile') == []

    def test_healthcheck_case_insensitive(self) -> None:
        src = 'FROM python:3.12-slim\nhealthcheck CMD curl -f http://localhost/health || exit 1\n'
        assert detect_missing_healthcheck(src, 'Dockerfile') == []


class TestDockerfileHealthcheckMain:
    def test_with_healthcheck_returns_0(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'Dockerfile',
            'FROM python:3.12-slim\nHEALTHCHECK CMD curl -f http://localhost/health || exit 1\n',
        )
        assert main([f]) == 0

    def test_missing_healthcheck_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.12-slim\nRUN echo ok\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
