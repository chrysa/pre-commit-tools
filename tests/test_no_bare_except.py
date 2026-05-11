"""Tests for no_bare_except."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_bare_except import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestNoBareExceptMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'try:\n    pass\nexcept ValueError:\n    pass\n')
        assert main([f]) == 0

    def test_bare_except_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'try:\n    pass\nexcept:\n    pass\n')
        assert main([f]) == 1

    def test_except_exception_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'try:\n    pass\nexcept Exception:\n    pass\n')
        assert main([f]) == 0

    def test_except_star_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'try:\n    pass\nexcept* ValueError:\n    pass\n')
        assert main([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'ok.py',
            'try:\n    pass\nexcept:  # no-bare-except: disable\n    pass\n',
        )
        assert main([f]) == 0

    def test_commented_except_ok(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', '# except:\n')
        assert main([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
