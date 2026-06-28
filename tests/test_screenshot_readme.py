"""Tests for screenshot_sync.publish.readme."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.screenshot_sync.manifest import Shot
from pre_commit_hooks.screenshot_sync.publish import readme

_SHOTS = [
    Shot(name='login', path='docs/screenshots/login.png', url='/login'),
    Shot(name='home', path='docs/screenshots/home.png', url='/'),
]


class TestRenderSection:
    def test_one_image_line_per_shot(self) -> None:
        section = readme.render_section(_SHOTS)
        assert '![login](docs/screenshots/login.png)' in section
        assert '![home](docs/screenshots/home.png)' in section


class TestInject:
    def test_replaces_between_existing_markers(self) -> None:
        text = '# Title\n\n<!-- shots:start -->\nOLD\n<!-- shots:end -->\n'
        result = readme.inject(text, 'NEW', 'shots')
        assert 'OLD' not in result
        assert 'NEW' in result
        assert result.count('<!-- shots:start -->') == 1

    def test_appends_markers_when_absent(self) -> None:
        result = readme.inject('# Title\n', 'BODY', 'shots')
        assert '<!-- shots:start -->' in result
        assert '<!-- shots:end -->' in result
        assert 'BODY' in result

    def test_idempotent(self) -> None:
        once = readme.inject('# Title\n', 'BODY', 'shots')
        twice = readme.inject(once, 'BODY', 'shots')
        assert once == twice


class TestUpdateReadmeFile:
    def test_creates_section_and_reports_change(self, tmp_path: Path) -> None:
        path = tmp_path / 'README.md'
        path.write_text('# Project\n', encoding='utf-8')
        changed = readme.update_readme_file(path, _SHOTS, 'screenshots')
        assert changed is True
        body = path.read_text(encoding='utf-8')
        assert '<!-- screenshots:start -->' in body
        assert '![login](docs/screenshots/login.png)' in body

    def test_no_change_returns_false(self, tmp_path: Path) -> None:
        path = tmp_path / 'README.md'
        path.write_text('# Project\n', encoding='utf-8')
        readme.update_readme_file(path, _SHOTS, 'screenshots')
        changed_again = readme.update_readme_file(path, _SHOTS, 'screenshots')
        assert changed_again is False
