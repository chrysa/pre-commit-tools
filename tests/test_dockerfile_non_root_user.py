"""Tests for dockerfile_non_root_user."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.dockerfile_non_root_user import detect_root_user, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectRootUser:
    def test_non_root_user_ok(self) -> None:
        src = 'FROM python:3.12-slim\nUSER appuser\n'
        assert detect_root_user(src, 'Dockerfile') == []

    def test_numeric_user_ok(self) -> None:
        src = 'FROM python:3.12-slim\nUSER 1001\n'
        assert detect_root_user(src, 'Dockerfile') == []

    def test_missing_user_detected(self) -> None:
        src = 'FROM python:3.12-slim\nRUN pip install app\n'
        violations = detect_root_user(src, 'Dockerfile')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'USER' in msg

    def test_user_root_detected(self) -> None:
        src = 'FROM python:3.12-slim\nUSER root\n'
        violations = detect_root_user(src, 'Dockerfile')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'root' in msg

    def test_multi_stage_checks_final_stage_only(self) -> None:
        src = 'FROM python:3.12 AS builder\nUSER root\nFROM python:3.12-slim\nUSER appuser\n'
        assert detect_root_user(src, 'Dockerfile') == []

    def test_multi_stage_final_stage_no_user(self) -> None:
        src = 'FROM python:3.12 AS builder\nUSER appuser\nFROM python:3.12-slim\nRUN echo ok\n'
        violations = detect_root_user(src, 'Dockerfile')
        assert len(violations) == 1

    def test_disable_comment_suppresses(self) -> None:
        src = '# dockerfile-non-root-user: disable\nFROM python:3.12-slim\n'
        assert detect_root_user(src, 'Dockerfile') == []

    def test_empty_dockerfile_no_violation(self) -> None:
        src = '# just a comment\n'
        assert detect_root_user(src, 'Dockerfile') == []

    def test_user_case_insensitive(self) -> None:
        src = 'FROM python:3.12-slim\nuser appuser\n'
        assert detect_root_user(src, 'Dockerfile') == []


class TestDockerfileNonRootUserMain:
    def test_non_root_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.12-slim\nUSER appuser\n')
        assert main([f]) == 0

    def test_no_user_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.12-slim\nRUN echo ok\n')
        assert main([f]) == 1

    def test_user_root_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'Dockerfile', 'FROM python:3.12-slim\nUSER root\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
