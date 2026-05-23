"""Tests for helm_lint hook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from pre_commit_hooks.helm_lint import _find_charts, main


def _make_chart(base: Path, namespace: str, service: str) -> Path:
    chart_dir = base / namespace / service
    chart_dir.mkdir(parents=True)
    (chart_dir / 'Chart.yaml').write_text('apiVersion: v2\nname: svc\nversion: 0.1.0\n', encoding='utf-8')
    return chart_dir


class TestFindCharts:
    def test_finds_charts_with_chart_yaml(self, tmp_path: Path) -> None:
        chart = _make_chart(tmp_path, 'dev', 'my-app')
        found = _find_charts(tmp_path)
        assert chart in found

    def test_ignores_dirs_without_chart_yaml(self, tmp_path: Path) -> None:
        (tmp_path / 'dev' / 'no-chart').mkdir(parents=True)
        assert _find_charts(tmp_path) == []

    def test_missing_root_returns_empty(self, tmp_path: Path) -> None:
        assert _find_charts(tmp_path / 'nonexistent') == []


class TestHelmLintMain:
    def test_no_helm_in_path_returns_0(self, tmp_path: Path) -> None:
        _make_chart(tmp_path, 'dev', 'my-app')
        with patch('pre_commit_hooks.helm_lint.shutil.which', return_value=None):
            assert main(['--charts-dir', str(tmp_path)]) == 0

    def test_missing_charts_dir_returns_0(self, tmp_path: Path) -> None:
        with patch('pre_commit_hooks.helm_lint.shutil.which', return_value='/usr/bin/helm'):
            assert main(['--charts-dir', str(tmp_path / 'nonexistent')]) == 0

    def test_helm_success_returns_0(self, tmp_path: Path) -> None:
        _make_chart(tmp_path, 'dev', 'my-app')
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch('pre_commit_hooks.helm_lint.shutil.which', return_value='/usr/bin/helm'),
            patch('pre_commit_hooks.helm_lint.subprocess.run', return_value=mock_result),
        ):
            assert main(['--charts-dir', str(tmp_path)]) == 0

    def test_helm_failure_returns_1(self, tmp_path: Path) -> None:
        _make_chart(tmp_path, 'dev', 'bad-chart')
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = 'Error: lint failed\n'
        mock_result.stderr = ''
        with (
            patch('pre_commit_hooks.helm_lint.shutil.which', return_value='/usr/bin/helm'),
            patch('pre_commit_hooks.helm_lint.subprocess.run', return_value=mock_result),
        ):
            assert main(['--charts-dir', str(tmp_path)]) == 1

    def test_multiple_charts_one_fails_returns_1(self, tmp_path: Path) -> None:
        _make_chart(tmp_path, 'dev', 'good')
        _make_chart(tmp_path, 'dev', 'bad')
        results = [MagicMock(returncode=0, stdout='', stderr=''), MagicMock(returncode=1, stdout='fail\n', stderr='')]
        with (
            patch('pre_commit_hooks.helm_lint.shutil.which', return_value='/usr/bin/helm'),
            patch('pre_commit_hooks.helm_lint.subprocess.run', side_effect=results),
        ):
            assert main(['--charts-dir', str(tmp_path)]) == 1
