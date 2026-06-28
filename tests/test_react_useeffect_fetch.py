"""Tests for react_useeffect_fetch."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.react_useeffect_fetch import main


def _tsx(tmp_path: Path, body: str) -> str:
    p = tmp_path / 'C.tsx'
    p.write_text(body, encoding='utf-8')
    return str(p)


_FETCH_EFFECT = 'useEffect(() => {\n  fetch("/api/x").then(setData)\n}, [])\n'
_AXIOS_EFFECT = 'useEffect(() => {\n  axios.get("/api/x")\n}, [])\n'
_CLEAN_EFFECT = 'useEffect(() => {\n  const id = setInterval(tick, 1000)\n  return () => clearInterval(id)\n}, [])\n'


class TestReactUseEffectFetch:
    def test_fetch_in_useeffect_flagged(self, tmp_path: Path) -> None:
        assert main([_tsx(tmp_path, _FETCH_EFFECT)]) == 1

    def test_axios_in_useeffect_flagged(self, tmp_path: Path) -> None:
        assert main([_tsx(tmp_path, _AXIOS_EFFECT)]) == 1

    def test_non_fetch_effect_ok(self, tmp_path: Path) -> None:
        assert main([_tsx(tmp_path, _CLEAN_EFFECT)]) == 0

    def test_disable_comment_skips(self, tmp_path: Path) -> None:
        body = 'useEffect(() => {  // react-useeffect-fetch: disable\n  fetch("/api/x")\n}, [])\n'
        assert main([_tsx(tmp_path, body)]) == 0
