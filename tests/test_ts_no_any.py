"""Tests for ts_no_any."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.ts_no_any import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


@pytest.mark.parametrize(
    'stmt',
    [
        'const x: any = value;\n',
        'function foo(x: any): void {}\n',
        'const y = value as any;\n',
        'const z = (<any>value);\n',
    ],
)
class TestTsNoAnyDetection:
    def test_any_usage_returns_1(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'bad.ts', stmt)
        assert main([f]) == 1

    def test_disable_comment_suppresses(self, tmp_path: Path, stmt: str) -> None:
        line = stmt.rstrip('\n') + '  // ts-no-any: disable\n'
        f = _write(tmp_path, 'ok.ts', line)
        assert main([f]) == 0

    def test_commented_line_suppressed(self, tmp_path: Path, stmt: str) -> None:
        f = _write(tmp_path, 'ok.ts', '// ' + stmt)
        assert main([f]) == 0


class TestTsNoAnyClean:
    def test_typed_param_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.ts', 'function foo(x: string): void {}\n')
        assert main([f]) == 0

    def test_unknown_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.ts', 'const x: unknown = value;\n')
        assert main([f]) == 0

    def test_empty_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.ts', '')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
