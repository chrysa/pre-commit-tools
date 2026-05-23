"""Tests for fastapi_missing_links hook."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.fastapi_missing_links import detect_missing_links, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


_ROUTE_WITH_LINKS = """\
from pydantic import BaseModel

class ItemResponse(BaseModel):
    id: int
    links: dict

@router.get("/items/{id}", response_model=ItemResponse)
async def get_item(id: int):
    pass
"""

_ROUTE_WITHOUT_LINKS = """\
from pydantic import BaseModel

class ItemResponse(BaseModel):
    id: int

@router.get("/items/{id}", response_model=ItemResponse)
async def get_item(id: int):
    pass
"""


class TestDetectMissingLinks:
    def test_model_with_links_returns_empty(self) -> None:
        assert detect_missing_links(_ROUTE_WITH_LINKS, 'f.py') == []

    def test_model_without_links_returns_violation(self) -> None:
        result = detect_missing_links(_ROUTE_WITHOUT_LINKS, 'f.py')
        assert len(result) == 1
        assert 'links' in result[0][2]

    def test_no_response_model_not_flagged(self) -> None:
        src = """\
@router.get("/ping")
async def ping():
    pass
"""
        assert detect_missing_links(src, 'f.py') == []

    def test_disable_comment_suppresses(self) -> None:
        src = """\
from pydantic import BaseModel

class ItemResponse(BaseModel):
    id: int

@router.get("/items", response_model=ItemResponse)  # fastapi-missing-links: disable
async def list_items():
    pass
"""
        assert detect_missing_links(src, 'f.py') == []

    def test_list_response_model_checked(self) -> None:
        src = """\
from pydantic import BaseModel

class ItemResponse(BaseModel):
    id: int

@router.get("/items", response_model=list[ItemResponse])
async def list_items():
    pass
"""
        result = detect_missing_links(src, 'f.py')
        assert len(result) == 1

    def test_syntax_error_returns_empty(self) -> None:
        assert detect_missing_links('def invalid(', 'f.py') == []

    def test_unknown_model_not_flagged(self) -> None:
        # Model defined in another file — cannot inspect it, skip
        src = """\
@router.get("/items", response_model=ExternalModel)
async def get_items():
    pass
"""
        assert detect_missing_links(src, 'f.py') == []


class TestFastapiMissingLinksMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'ok.py', _ROUTE_WITH_LINKS)
        assert main([f]) == 0

    def test_violation_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.py', _ROUTE_WITHOUT_LINKS)
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
