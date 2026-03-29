"""Tests for dead_code_detection (requires vulture)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pre_commit_hooks.dead_code_detection import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDeadCodeDetectionMain:
    def test_missing_vulture_returns_1(self) -> None:
        with patch.dict('sys.modules', {'vulture': None}):
            result = main([])
        assert result == 1

    def test_no_unused_code_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'def used() -> int:\n    return 1\nused()\n')
        # vulture may or may not be installed in CI — skip if absent
        pytest.importorskip('vulture')
        assert main([f]) == 0

    def test_unused_function_returns_1(self, tmp_path: Path) -> None:
        """Unused function with 100% confidence should be reported."""
        pytest.importorskip('vulture')
        f = _write(tmp_path, 'dead.py', 'def _never_called() -> None:\n    pass\n')
        # vulture confidence may vary; mock get_unused_code to force a result
        mock_item = MagicMock()
        mock_item.filename = str(f)
        mock_item.first_lineno = 1
        mock_item.typ = 'function'
        mock_item.name = '_never_called'

        import vulture as vlt

        with patch.object(vlt.Vulture, 'get_unused_code', return_value=[mock_item]):
            result = main(['--min-confidence=60', f])
        assert result == 1

    def test_empty_args_with_vulture_returns_0(self) -> None:
        pytest.importorskip('vulture')
        assert main([]) == 0
