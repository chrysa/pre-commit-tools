"""Tests for js_syntax_check hook."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pre_commit_hooks.js_syntax_check import check_syntax, main

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestCheckSyntax:
    def test_node_not_found_returns_error(self, mocker: MockerFixture) -> None:
        mocker.patch('subprocess.run', side_effect=FileNotFoundError)
        result = check_syntax('f.js')
        assert len(result) == 1
        assert 'node check failed' in result[0][1]

    def test_syntax_error_returns_violation(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'SyntaxError: Unexpected token'
        mock_result.stdout = ''
        mocker.patch('subprocess.run', return_value=mock_result)
        result = check_syntax('bad.js')
        assert len(result) == 1
        assert 'SyntaxError' in result[0][1]

    def test_clean_file_returns_empty(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        mocker.patch('subprocess.run', return_value=mock_result)
        assert check_syntax('good.js') == []


class TestJsSyntaxCheckMain:
    def test_node_not_available_returns_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        f = _write(tmp_path, 'a.js', 'const x = 1;\n')
        mocker.patch('pre_commit_hooks.js_syntax_check._check_node_available', return_value=False)
        assert main([f]) == 0

    def test_clean_js_returns_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        f = _write(tmp_path, 'a.js', 'const x = 1;\n')
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mocker.patch('pre_commit_hooks.js_syntax_check._check_node_available', return_value=True)
        mocker.patch('subprocess.run', return_value=mock_result)
        assert main([f]) == 0

    def test_syntax_error_returns_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        f = _write(tmp_path, 'bad.js', 'const = ;\n')
        mock_result = mocker.MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'SyntaxError'
        mock_result.stdout = ''
        mocker.patch('pre_commit_hooks.js_syntax_check._check_node_available', return_value=True)
        mocker.patch('subprocess.run', return_value=mock_result)
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0


class TestCheckViaTempJs:
    def test_gs_file_clean_returns_empty(self, tmp_path: Path, mocker: MockerFixture) -> None:
        from pre_commit_hooks.js_syntax_check import _check_via_temp_js

        f = _write(tmp_path, 'a.gs', 'var x = 1;\n')
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        mocker.patch('subprocess.run', return_value=mock_result)
        assert _check_via_temp_js(f) == []

    def test_gs_file_syntax_error_returns_violation(self, tmp_path: Path, mocker: MockerFixture) -> None:
        from pre_commit_hooks.js_syntax_check import _check_via_temp_js

        f = _write(tmp_path, 'bad.gs', 'var = ;\n')
        mock_result = mocker.MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'SyntaxError: Unexpected token'
        mock_result.stdout = ''
        mocker.patch('subprocess.run', return_value=mock_result)
        result = _check_via_temp_js(f)
        assert len(result) == 1
        # Original filename preserved in violation
        assert result[0][0] == f

    def test_gs_file_routes_through_temp_js(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """check_syntax() must use _check_via_temp_js for .gs files."""
        f = _write(tmp_path, 'a.gs', 'var x = 1;\n')
        mock_fn = mocker.patch('pre_commit_hooks.js_syntax_check._check_via_temp_js', return_value=[])
        check_syntax(f)
        mock_fn.assert_called_once_with(f)
