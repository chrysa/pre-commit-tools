"""Tests for compose_dev_hot_reload."""

from __future__ import annotations

from pathlib import Path

from pre_commit_hooks.compose_dev_hot_reload import detect_dev_without_hot_reload, main

BAKED_DEV = (
    'services:\n  api:\n    build:\n      context: .\n      target: dev\n    command: uvicorn app:app --reload\n'
)
BIND_MOUNTED_DEV = (
    'services:\n  api:\n    build:\n      context: .\n      target: dev\n'
    '    volumes:\n      - .:/code\n      - node-modules:/code/node_modules\n'
)
WATCHED_DEV = (
    'services:\n  web:\n    build:\n      target: development\n'
    '    develop:\n      watch:\n        - action: sync\n          path: ./src\n          target: /code/src\n'
)
LONG_FORM_MOUNT_DEV = (
    'services:\n  api:\n    build: {target: dev}\n'
    '    volumes:\n      - type: bind\n        source: ./app\n        target: /code/app\n'
)
NAMED_VOLUME_DEV = 'services:\n  api:\n    build: {target: dev}\n    volumes:\n      - cache:/code/.cache\n'
REBUILD_WATCH_DEV = (
    'services:\n  api:\n    build: {target: dev}\n'
    '    develop:\n      watch:\n        - action: rebuild\n          path: ./src\n'
)
CUSTOM_TARGET_DEV = 'services:\n  api:\n    build: {target: local}\n'


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectDevWithoutHotReload:
    def test_dev_target_without_source_access_detected(self) -> None:
        violations = detect_dev_without_hot_reload(BAKED_DEV, 'compose.yaml')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'hot-reload' in msg
        assert "'api'" in msg

    def test_bind_mount_is_enough(self) -> None:
        assert detect_dev_without_hot_reload(BIND_MOUNTED_DEV, 'compose.yaml') == []

    def test_develop_watch_sync_is_enough(self) -> None:
        assert detect_dev_without_hot_reload(WATCHED_DEV, 'compose.yaml') == []

    def test_long_form_bind_mount_is_enough(self) -> None:
        assert detect_dev_without_hot_reload(LONG_FORM_MOUNT_DEV, 'compose.yaml') == []

    def test_named_volume_alone_is_not_enough(self) -> None:
        assert len(detect_dev_without_hot_reload(NAMED_VOLUME_DEV, 'compose.yaml')) == 1

    def test_service_named_dev_is_covered(self) -> None:
        src = 'services:\n  dev:\n    image: app:local\n'
        assert len(detect_dev_without_hot_reload(src, 'compose.yaml')) == 1

    def test_service_suffixed_dev_is_covered(self) -> None:
        src = 'services:\n  worker-dev:\n    image: app:local\n'
        assert len(detect_dev_without_hot_reload(src, 'compose.yaml')) == 1

    def test_production_service_ignored(self) -> None:
        src = 'services:\n  api:\n    build: {target: production}\n'
        assert detect_dev_without_hot_reload(src, 'compose.yaml') == []

    def test_watch_without_sync_action_detected(self) -> None:
        assert len(detect_dev_without_hot_reload(REBUILD_WATCH_DEV, 'compose.yaml')) == 1

    def test_custom_target_name(self) -> None:
        assert detect_dev_without_hot_reload(CUSTOM_TARGET_DEV, 'compose.yaml') == []
        assert len(detect_dev_without_hot_reload(CUSTOM_TARGET_DEV, 'compose.yaml', targets=('local',))) == 1

    def test_disable_comment_skips_file(self) -> None:
        src = '# compose-dev-hot-reload: disable\n' + BAKED_DEV
        assert detect_dev_without_hot_reload(src, 'compose.yaml') == []

    def test_invalid_yaml_is_ignored(self) -> None:
        assert detect_dev_without_hot_reload('services: [unclosed', 'compose.yaml') == []

    def test_document_without_services_ignored(self) -> None:
        assert detect_dev_without_hot_reload('version: "3.9"\n', 'compose.yaml') == []

    def test_non_mapping_document_ignored(self) -> None:
        assert detect_dev_without_hot_reload('- just\n- a list\n', 'compose.yaml') == []

    def test_non_mapping_service_ignored(self) -> None:
        assert detect_dev_without_hot_reload('services:\n  dev: null\n', 'compose.yaml') == []


class TestMain:
    def test_main_returns_one_on_violation(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'compose.yaml', BAKED_DEV)
        assert main([path]) == 1

    def test_main_returns_zero_when_clean(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'compose.yaml', BIND_MOUNTED_DEV)
        assert main([path]) == 0

    def test_main_honours_target_flag(self, tmp_path: Path) -> None:
        path = _write(tmp_path, 'compose.yaml', CUSTOM_TARGET_DEV)
        assert main([path]) == 0
        assert main([path, '--target', 'local']) == 1

    def test_main_skips_unreadable_file(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'missing.yaml')]) == 0
