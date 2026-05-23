"""Tests for no_hardcoded_localhost hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.no_hardcoded_localhost import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestNoHardcodedLocalhostMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', 'BASE_URL = os.environ["BASE_URL"]\n')
        assert main([f]) == 0

    def test_localhost_url_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'BASE_URL = "http://localhost:8000/api"\n')
        assert main([f]) == 1

    def test_127_url_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'URL = "http://127.0.0.1:5000/"\n')
        assert main([f]) == 1

    def test_https_localhost_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', 'url = "https://localhost/api"\n')
        assert main([f]) == 1

    def test_commented_line_not_flagged_python(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', '# BASE_URL = "http://localhost:8000"\n')
        assert main([f]) == 0

    def test_commented_line_not_flagged_ts(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.ts', '// const url = "http://localhost:3000"\n')
        assert main([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path,
            'ok.py',
            'BASE_URL = "http://localhost:8000"  # no-hardcoded-localhost: disable\n',
        )
        assert main([f]) == 0

    def test_multiple_files_any_bad_returns_1(self, tmp_path: Path) -> None:
        clean = _write(tmp_path, 'clean.py', 'x = 1\n')
        bad = _write(tmp_path, 'bad.py', 'url = "http://127.0.0.1:8080/"\n')
        assert main([clean, bad]) == 1

    def test_empty_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'empty.py', '')
        assert main([f]) == 0
