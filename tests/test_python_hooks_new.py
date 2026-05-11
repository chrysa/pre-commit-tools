"""Tests for no_sync_in_async and fastapi_missing_response_model hooks."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.fastapi_missing_response_model import (
    detect_missing_response_model,
)
from pre_commit_hooks.fastapi_missing_response_model import main as main_fastapi
from pre_commit_hooks.no_sync_in_async import detect_sync_in_async
from pre_commit_hooks.no_sync_in_async import main as main_sync


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectSyncInAsync:
    def test_time_sleep_in_async_detected(self) -> None:
        src = 'import time\nasync def handler():\n    time.sleep(1)\n'
        violations = detect_sync_in_async(src, 'f.py')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'time.sleep' in msg

    def test_requests_get_in_async_detected(self) -> None:
        src = 'import requests\nasync def fetch():\n    requests.get("http://example.com")\n'
        violations = detect_sync_in_async(src, 'f.py')
        assert len(violations) == 1
        assert 'requests.get' in violations[0][2]

    def test_blocking_in_sync_function_ignored(self) -> None:
        src = 'import time\ndef handler():\n    time.sleep(1)\n'
        assert detect_sync_in_async(src, 'f.py') == []

    def test_asyncio_sleep_ok(self) -> None:
        src = 'import asyncio\nasync def handler():\n    await asyncio.sleep(1)\n'
        assert detect_sync_in_async(src, 'f.py') == []

    def test_disable_comment_suppresses(self) -> None:
        src = 'import time\nasync def handler():\n    time.sleep(1)  # no-sync-in-async: disable\n'
        assert detect_sync_in_async(src, 'f.py') == []

    def test_syntax_error_returns_empty(self) -> None:
        assert detect_sync_in_async('def (:', 'bad.py') == []


class TestNoSyncInAsyncMain:
    def test_violation_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.py', 'import time\nasync def h():\n    time.sleep(1)\n')
        assert main_sync([f]) == 1

    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.py', 'async def h():\n    pass\n')
        assert main_sync([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main_sync([]) == 0


class TestDetectMissingResponseModel:
    def test_route_without_response_model_detected(self) -> None:
        src = (
            'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/items")\nasync def get_items():\n    return []\n'
        )
        violations = detect_missing_response_model(src, 'f.py')
        assert len(violations) == 1
        assert 'get_items' in violations[0][2]

    def test_route_with_response_model_ok(self) -> None:
        src = (
            'from fastapi import FastAPI\napp = FastAPI()\n'
            '@app.get("/items", response_model=list)\nasync def get_items():\n    return []\n'
        )
        assert detect_missing_response_model(src, 'f.py') == []

    def test_post_without_response_model_detected(self) -> None:
        src = 'from fastapi import FastAPI\napp = FastAPI()\n@app.post("/items")\ndef create_item():\n    return {}\n'
        violations = detect_missing_response_model(src, 'f.py')
        assert len(violations) == 1

    def test_non_route_decorator_ignored(self) -> None:
        src = '@staticmethod\ndef helper():\n    pass\n'
        assert detect_missing_response_model(src, 'f.py') == []

    def test_disable_comment_suppresses(self) -> None:
        src = '@app.get("/items")  # fastapi-missing-response-model: disable\nasync def get_items():\n    return []\n'
        assert detect_missing_response_model(src, 'f.py') == []

    def test_syntax_error_returns_empty(self) -> None:
        assert detect_missing_response_model('def (:', 'bad.py') == []


class TestFastapiMissingResponseModelMain:
    def test_violation_returns_1(self, tmp_path: Path) -> None:
        src = 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/x")\nasync def f():\n    return {}\n'
        f = _write(tmp_path, 'a.py', src)
        assert main_fastapi([f]) == 1

    def test_clean_returns_0(self, tmp_path: Path) -> None:
        src = (
            'from fastapi import FastAPI\napp = FastAPI()\n'
            '@app.get("/x", response_model=dict)\nasync def f():\n    return {}\n'
        )
        f = _write(tmp_path, 'a.py', src)
        assert main_fastapi([f]) == 0

    def test_empty_args_returns_0(self) -> None:
        assert main_fastapi([]) == 0
