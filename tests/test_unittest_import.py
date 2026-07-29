"""Tests for unittest_import."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.unittest_import import main


def _py(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'm.py'
    p.write_text(body, encoding='utf-8')
    return str(p)


class TestUnittestImport:
    def test_plain_import_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'import unittest\n')]) == 1

    def test_mock_import_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'from unittest.mock import AsyncMock, patch\n')]) == 1

    def test_submodule_import_flagged(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'import unittest.mock\n')]) == 1

    def test_pytest_mock_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'import pytest\nfrom pytest_mock import MockerFixture\n')]) == 0

    def test_unrelated_name_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'from myproject.unittests import helper\n')]) == 0

    def test_word_in_string_ok(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'msg = "migrated away from unittest"\n')]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, 'import unittest  # unittest-import: disable\n')]) == 0

    def test_commented_line_skipped(self, tmp_path: Path) -> None:
        assert main([_py(tmp_path, '# import unittest\n')]) == 0
