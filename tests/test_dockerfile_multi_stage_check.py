"""Tests for dockerfile_multi_stage_check."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.dockerfile_multi_stage_check import detect_missing_multi_stage, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectMissingMultiStage:
    def test_single_stage_detected(self) -> None:
        src = 'FROM python:3.12-slim\nRUN pip install app\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'multi-stage' in msg.lower()

    def test_multi_stage_ok(self) -> None:
        src = 'FROM python:3.12 AS builder\nRUN pip install app\nFROM python:3.12-slim\nCOPY --from=builder /app /app\n'
        assert detect_missing_multi_stage(src, 'Dockerfile') == []

    def test_three_stages_ok(self) -> None:
        src = 'FROM node:18 AS deps\nFROM node:18 AS builder\nFROM nginx:1.25\n'
        assert detect_missing_multi_stage(src, 'Dockerfile') == []

    def test_from_scratch_only_detected(self) -> None:
        src = 'FROM scratch\nCOPY app /app\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile')
        assert len(violations) == 1

    def test_from_scratch_plus_real_ok(self) -> None:
        src = 'FROM golang:1.21 AS builder\nRUN go build\nFROM scratch\nCOPY --from=builder /app /app\n'
        assert detect_missing_multi_stage(src, 'Dockerfile') == []

    def test_empty_dockerfile_no_violation(self) -> None:
        src = '# just a comment\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile')
        assert len(violations) == 1

    def test_disable_comment_suppresses(self) -> None:
        src = '# dockerfile-multi-stage-check: disable\nFROM python:3.12\n'
        assert detect_missing_multi_stage(src, 'Dockerfile') == []

    def test_comment_line_ignored(self) -> None:
        src = '# FROM python:3.12\nFROM python:3.12-slim\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile')
        assert len(violations) == 1


class TestDockerfileMultiStageCheckMain:
    def test_multi_stage_returns_0(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'Dockerfile',
            'FROM python:3.12 AS builder\nFROM python:3.12-slim\n',
        )
        assert main([f]) == 0

    def test_single_stage_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.12-slim\nRUN echo ok\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
