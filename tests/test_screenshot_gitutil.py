"""Tests for screenshot_sync.gitutil and reporting."""

from __future__ import annotations

import pytest

from pre_commit_hooks.screenshot_sync import gitutil, reporting


class TestGitAdd:
    def test_calls_git_add_with_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[list[str]] = []
        monkeypatch.setattr(gitutil.subprocess, 'run', lambda cmd, **kw: calls.append(cmd))
        gitutil.git_add(['docs/screenshots', 'README.md'])
        assert calls == [['git', 'add', '--', 'docs/screenshots', 'README.md']]

    def test_empty_paths_is_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[list[str]] = []
        monkeypatch.setattr(gitutil.subprocess, 'run', lambda cmd, **kw: calls.append(cmd))
        gitutil.git_add([])
        assert calls == []


class TestReporting:
    def test_skip_returns_zero_when_not_strict(self, capsys: pytest.CaptureFixture) -> None:
        assert reporting.skip_or_fail(False, 'boom') == 0
        assert '[screenshot-sync] boom' in capsys.readouterr().out

    def test_fail_returns_one_when_strict(self, capsys: pytest.CaptureFixture) -> None:
        assert reporting.skip_or_fail(True, 'boom') == 1
        assert '[screenshot-sync] boom' in capsys.readouterr().out
