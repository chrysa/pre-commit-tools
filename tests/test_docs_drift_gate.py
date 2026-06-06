"""Tests for docs_drift_gate hook."""

from __future__ import annotations

import subprocess

import pre_commit_hooks.docs_drift_gate as mod
from pre_commit_hooks.docs_drift_gate import main


def _cp(returncode: int = 0, stdout: str = '', stderr: str = '') -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class _FakeRun:
    def __init__(self, make_rc: int = 0, diff_rc: int = 0, stat: str = ' docs/api/openapi.json | 2 +-') -> None:
        self.make_rc = make_rc
        self.diff_rc = diff_rc
        self.stat = stat
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], *a: object, **k: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(cmd)
        if cmd[0] == 'make':
            return _cp(returncode=self.make_rc, stderr='boom' if self.make_rc else '')
        if cmd[:2] == ['git', 'diff'] and '--exit-code' in cmd:
            return _cp(returncode=self.diff_rc)
        if cmd[:2] == ['git', 'diff'] and '--stat' in cmd:
            return _cp(returncode=0, stdout=self.stat)
        return _cp()


class TestDocsDriftGate:
    def test_clean_returns_0(self, monkeypatch) -> None:
        fake = _FakeRun(make_rc=0, diff_rc=0)
        monkeypatch.setattr(mod.subprocess, 'run', fake)
        assert main([]) == 0
        assert ['make', 'docs-code'] in fake.calls

    def test_drift_returns_1(self, monkeypatch) -> None:
        fake = _FakeRun(make_rc=0, diff_rc=1)
        monkeypatch.setattr(mod.subprocess, 'run', fake)
        assert main([]) == 1

    def test_make_failure_returns_1_and_skips_diff(self, monkeypatch) -> None:
        fake = _FakeRun(make_rc=2)
        monkeypatch.setattr(mod.subprocess, 'run', fake)
        assert main([]) == 1
        assert all(c[0] != 'git' for c in fake.calls)

    def test_custom_target_and_paths_forwarded(self, monkeypatch) -> None:
        fake = _FakeRun(make_rc=0, diff_rc=0)
        monkeypatch.setattr(mod.subprocess, 'run', fake)
        assert main(['--target', 'docs', '--paths', 'docs/', 'public/']) == 0
        assert ['make', 'docs'] in fake.calls
        diff_call = next(c for c in fake.calls if c[:2] == ['git', 'diff'] and '--exit-code' in c)
        assert diff_call[-2:] == ['docs/', 'public/']
