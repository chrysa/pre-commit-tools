"""Tests for django_hardcoded_secret."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.django_hardcoded_secret import detect_hardcoded_secrets, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectHardcodedSecrets:
    def test_env_reference_is_safe(self) -> None:
        src = 'SECRET_KEY = os.environ.get("SECRET_KEY")\n'
        assert detect_hardcoded_secrets(src, 'settings.py') == []

    def test_hardcoded_secret_key_detected(self) -> None:
        src = 'SECRET_KEY = "django-insecure-abc123xyz456"\n'
        violations = detect_hardcoded_secrets(src, 'settings.py')
        assert len(violations) == 1
        _fname, _lineno, msg = violations[0]
        assert 'SECRET_KEY' in msg

    def test_hardcoded_password_detected(self) -> None:
        src = 'DATABASE_PASSWORD = "supersecret"\n'
        violations = detect_hardcoded_secrets(src, 'settings.py')
        assert len(violations) == 1

    def test_getenv_reference_is_safe(self) -> None:
        src = 'PASSWORD = os.getenv("DB_PASS", "")\n'
        assert detect_hardcoded_secrets(src, 'settings.py') == []

    def test_env_function_is_safe(self) -> None:
        src = 'SECRET_KEY = env("SECRET_KEY")\n'
        assert detect_hardcoded_secrets(src, 'settings.py') == []

    def test_disable_comment_suppresses(self) -> None:
        src = 'SECRET_KEY = "abc123xyz456"  # django-hardcoded-secret: disable\n'
        assert detect_hardcoded_secrets(src, 'settings.py') == []

    @pytest.mark.parametrize(
        'src',
        [
            'API_KEY = "mykey1234"\n',
            'MY_TOKEN = "tok_abc123"\n',
            'PRIVATE_KEY = "-----BEGIN RSA-----"\n',
        ],
    )
    def test_various_secret_patterns(self, src: str) -> None:
        violations = detect_hardcoded_secrets(src, 'settings.py')
        assert len(violations) == 1


class TestDjangoHardcodedSecretMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'settings.py', 'SECRET_KEY = os.environ["SECRET_KEY"]\n')
        assert main([f]) == 0

    def test_hardcoded_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'settings.py', 'SECRET_KEY = "hardcoded-secret-123"\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0
