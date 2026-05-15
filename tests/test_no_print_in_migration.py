"""Tests for no_print_in_migration."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_print_in_migration import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestNoPrintInMigrationMain:
    def test_clean_migration_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '0001_initial.py', 'class Migration:\n    pass\n')
        assert main([f]) == 0

    def test_print_in_migration_returns_1(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            '0001_initial.py',
            'class Migration:\n    def apply(self):\n        print("migrating")\n',
        )
        assert main([f]) == 1

    def test_commented_print_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, '0001_initial.py', '# print("debug")\n')
        assert main([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            '0001.py',
            'print("x")  # no-print-in-migration: disable\n',
        )
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
