"""Tests for dockerfile_no_latest."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.dockerfile_no_latest import detect_from_latest, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectFromLatest:
    def test_pinned_tag_ok(self) -> None:
        src = 'FROM python:3.12-slim\n'
        assert detect_from_latest(src, 'Dockerfile') == []

    def test_latest_detected(self) -> None:
        src = 'FROM python:latest\n'
        violations = detect_from_latest(src, 'Dockerfile')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'latest' in msg

    def test_from_scratch_ignored(self) -> None:
        src = 'FROM scratch\n'
        assert detect_from_latest(src, 'Dockerfile') == []

    def test_multi_stage_one_latest(self) -> None:
        src = 'FROM node:18 AS build\nFROM nginx:latest\n'
        violations = detect_from_latest(src, 'Dockerfile')
        assert len(violations) == 1

    def test_disable_comment_suppresses(self) -> None:
        src = 'FROM python:latest  # dockerfile-no-latest: disable\n'
        assert detect_from_latest(src, 'Dockerfile') == []

    def test_case_insensitive(self) -> None:
        src = 'FROM PYTHON:LATEST\n'
        assert len(detect_from_latest(src, 'Dockerfile')) == 1

    @pytest.mark.parametrize('src', [
        'FROM python:3.12\n',
        'FROM node:18-alpine\n',
        'FROM golang:1.21.0\n',
    ])
    def test_pinned_images_ok(self, src: str) -> None:
        assert detect_from_latest(src, 'Dockerfile') == []


class TestDockerfileNoLatestMain:
    def test_clean_dockerfile_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.12-slim\nRUN echo ok\n')
        assert main([f]) == 0

    def test_latest_dockerfile_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:latest\nRUN echo ok\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
