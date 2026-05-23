"""Tests for react_no_async_in_useeffect hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.react_no_async_in_useeffect import main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestReactNoAsyncInUseEffectMain:
    def test_clean_useeffect_returns_0(self, tmp_path: Path) -> None:
        src = 'useEffect(() => { fetchData(); }, []);\n'
        f = _write(tmp_path, 'ok.tsx', src)
        assert main([f]) == 0

    def test_async_useeffect_arrow_returns_1(self, tmp_path: Path) -> None:
        src = 'useEffect(async () => { await fetchData(); }, []);\n'
        f = _write(tmp_path, 'bad.tsx', src)
        assert main([f]) == 1

    def test_async_useeffect_function_keyword_returns_1(self, tmp_path: Path) -> None:
        src = 'useEffect(async function load() { await fetch("/api"); }, []);\n'
        f = _write(tmp_path, 'bad.tsx', src)
        assert main([f]) == 1

    def test_commented_line_not_flagged(self, tmp_path: Path) -> None:
        src = '// useEffect(async () => { await fetchData(); }, []);\n'
        f = _write(tmp_path, 'ok.tsx', src)
        assert main([f]) == 0

    def test_disable_comment_suppresses(self, tmp_path: Path) -> None:
        src = 'useEffect(async () => { await fetchData(); }, []); // react-no-async-in-useeffect: disable\n'
        f = _write(tmp_path, 'ok.tsx', src)
        assert main([f]) == 0

    def test_multiple_files_any_bad_returns_1(self, tmp_path: Path) -> None:
        clean = _write(tmp_path, 'clean.tsx', 'useEffect(() => {}, []);\n')
        bad = _write(tmp_path, 'bad.tsx', 'useEffect(async () => { await x(); }, []);\n')
        assert main([clean, bad]) == 1

    def test_empty_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'empty.tsx', '')
        assert main([f]) == 0
