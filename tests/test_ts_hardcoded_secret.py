"""Tests for ts_hardcoded_secret hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_commit_hooks.ts_hardcoded_secret import detect_hardcoded_secrets, main


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return str(p)


class TestDetectHardcodedSecrets:
    def test_clean_source_returns_empty(self) -> None:
        assert detect_hardcoded_secrets('const x = 1;\n', 'f.ts') == []

    def test_hardcoded_api_key_detected(self) -> None:
        src = 'const apiKey = "abc1234567890";\n'
        result = detect_hardcoded_secrets(src, 'f.ts')
        assert len(result) == 1
        assert 'API_KEY' in result[0][2]

    def test_hardcoded_token_detected(self) -> None:
        src = 'const token = "mytoken123456";\n'
        result = detect_hardcoded_secrets(src, 'f.ts')
        assert len(result) == 1
        assert 'TOKEN' in result[0][2]

    def test_hardcoded_password_detected(self) -> None:
        src = 'const password = "hunter2x1234";\n'
        result = detect_hardcoded_secrets(src, 'f.ts')
        assert len(result) == 1
        assert 'PASSWORD' in result[0][2]

    def test_aws_key_pattern_detected(self) -> None:
        # Use concatenation so the literal is not a detectable secret in source
        aws_key = 'AKIA' + 'IOSFODNN7EXAMPL3'
        src = f'const key = "{aws_key}";\n'
        result = detect_hardcoded_secrets(src, 'f.ts')
        assert len(result) == 1
        assert 'AWS_KEY' in result[0][2]

    def test_process_env_not_flagged(self) -> None:
        src = 'const apiKey = process.env.API_KEY;\n'
        assert detect_hardcoded_secrets(src, 'f.ts') == []

    def test_import_meta_env_not_flagged(self) -> None:
        src = 'const token = import.meta.env.TOKEN;\n'
        assert detect_hardcoded_secrets(src, 'f.ts') == []

    def test_disable_comment_suppresses(self) -> None:
        src = 'const apiKey = "abc1234567890"; // ts-hardcoded-secret: disable\n'
        assert detect_hardcoded_secrets(src, 'f.ts') == []

    def test_short_value_not_flagged(self) -> None:
        # Less than 4 chars — too short to be a real secret
        src = 'const token = "abc";\n'
        assert detect_hardcoded_secrets(src, 'f.ts') == []

    @pytest.mark.parametrize(
        'src,label',
        [
            # Use concatenation so literals are not detected by push protection scanners
            ('const githubToken = "' + 'ghp_' + 'B' * 36 + '"', 'GITHUB_TOKEN'),
            ('const stripeKey = "' + 'sk_live_' + 'C' * 24 + '"', 'STRIPE_KEY'),
        ],
    )
    def test_known_patterns_detected(self, src: str, label: str) -> None:
        result = detect_hardcoded_secrets(src, 'f.ts')
        assert len(result) == 1
        assert label in result[0][2]


class TestTsHardcodedSecretMain:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'a.ts', 'const x = 1;\n')
        assert main([f]) == 0

    def test_violation_returns_1(self, tmp_path: Path) -> None:
        f = _write(tmp_path, 'bad.ts', 'const apiKey = "abc1234567890";\n')
        assert main([f]) == 1

    def test_empty_args_returns_0(self) -> None:
        assert main([]) == 0

    def test_missing_file_skipped(self) -> None:
        assert main(['nonexistent.ts']) == 0
