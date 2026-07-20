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


class TestRequireTargets:
    def test_missing_dev_target_detected(self) -> None:
        src = 'FROM python:3.14 AS builder\nRUN pip install app\nFROM python:3.14-slim AS production\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile', ['production', 'dev'])
        assert len(violations) == 1
        assert "'dev'" in violations[0][2]

    def test_both_targets_present_ok(self) -> None:
        src = (
            'FROM python:3.14 AS base\nFROM base AS production\n'
            'RUN true\nFROM production AS dev\nRUN pip install pytest\n'
        )
        assert detect_missing_multi_stage(src, 'Dockerfile', ['production', 'dev']) == []

    def test_target_match_is_case_insensitive(self) -> None:
        src = 'FROM x AS builder\nFROM x AS Production\nFROM x AS DEV\n'
        assert detect_missing_multi_stage(src, 'Dockerfile', ['production', 'dev']) == []

    def test_both_targets_missing_two_violations(self) -> None:
        src = 'FROM x AS builder\nFROM x AS runtime\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile', ['production', 'dev'])
        assert len(violations) == 2

    def test_no_require_targets_keeps_default_behavior(self) -> None:
        src = 'FROM x AS builder\nFROM x AS runtime\n'
        assert detect_missing_multi_stage(src, 'Dockerfile') == []

    def test_single_stage_short_circuits_before_target_check(self) -> None:
        src = 'FROM python:3.14\n'
        violations = detect_missing_multi_stage(src, 'Dockerfile', ['production', 'dev'])
        assert len(violations) == 1
        assert 'multi-stage' in violations[0][2].lower()


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
