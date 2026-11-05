"""Tests for the shared PatternDetection engine, console factory and README updater."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pre_commit_hooks.tools.console_detection import console_call_detection
from pre_commit_hooks.tools.pattern_detection import PatternDetection
from pre_commit_hooks.tools.update_readme import update_readme


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


def _todo_detection() -> PatternDetection:
    return PatternDetection(
        commented=re.compile(r'^\s*#'),
        disable_comment=re.compile(r'todo: disable'),
        pattern=re.compile(r'\bTODO\b'),
    )


class TestPatternDetectionEngine:
    def test_reports_one_based_line_number(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = _write(tmp_path, 'a.txt', 'ok\nTODO here\n')
        assert _todo_detection().detect(argv=[f]) == 1
        assert f'[{f}:2]' in capsys.readouterr().out

    def test_non_utf8_file_is_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / 'bin.txt'
        p.write_bytes(b'\xff\xfeTODO\n')
        assert _todo_detection().detect(argv=[str(p)]) == 0

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert _todo_detection().detect(argv=[str(tmp_path / 'missing.txt')]) == 0


class TestConsoleCallDetection:
    @pytest.mark.parametrize(
        'line',
        [
            'console.log("x");',
            '  console.log("x");',
            'cond && console.log("x");',
            'foo(); console.log ("x");',
        ],
    )
    def test_detects_call(self, tmp_path: Path, line: str) -> None:
        f = _write(tmp_path, 'bad.js', f'{line}\n')
        assert console_call_detection(method='log', disable_id='console-log-detection').detect(argv=[f]) == 1

    @pytest.mark.parametrize(
        'line',
        [
            '// console.log("x");',
            'foo(); // console.log("x");',
            'consoleXlog("x");',
            'myconsole.log("x");',
            'console.log("x"); // console-log-detection: disable',
        ],
    )
    def test_ignores_non_calls(self, tmp_path: Path, line: str) -> None:
        f = _write(tmp_path, 'ok.js', f'{line}\n')
        assert console_call_detection(method='log', disable_id='console-log-detection').detect(argv=[f]) == 0


class TestUpdateReadme:
    def test_replaces_only_the_tagged_section(self, tmp_path: Path) -> None:
        readme = tmp_path / 'README.md'
        readme.write_text('head\n<!--S-->\nold\n<!--E-->\ntail\n', encoding='utf-8')
        update_readme(
            start_tag='<!--S-->',
            end_tag='<!--E-->',
            command='unused',
            command_content_processed='\nnew\n',
            readme_file_path=readme,
        )
        assert readme.read_text(encoding='utf-8') == 'head\n<!--S-->\nnew\n<!--E-->\ntail\n'

    def test_missing_tags_leave_file_unchanged(self, tmp_path: Path) -> None:
        readme = tmp_path / 'README.md'
        readme.write_text('no tags\n', encoding='utf-8')
        update_readme(
            start_tag='<!--S-->',
            end_tag='<!--E-->',
            command='unused',
            command_content_processed='x',
            readme_file_path=readme,
        )
        assert readme.read_text(encoding='utf-8') == 'no tags\n'
