"""Tests for the claude_mcp_config hook."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pre_commit_hooks.claude_mcp_config import check_mcp_config, check_server, main

VALID: dict[str, Any] = {
    'mcpServers': {
        'playwright': {'command': 'npx', 'args': ['@playwright/mcp@latest']},
        'sentry': {'type': 'http', 'url': 'https://mcp.sentry.dev/mcp'},
        'notion': {
            'command': 'npx',
            'args': ['-y', '@notionhq/notion-mcp-server'],
            'env': {'NOTION_API_KEY': '${NOTION_API_KEY}'},
        },
    },
}


def _write(tmp_path: Path, config: Any, name: str = '.mcp.json') -> Path:
    """Write *config* as JSON to ``<tmp_path>/<name>`` and return its path."""
    path = tmp_path / name
    path.write_text(json.dumps(config), encoding='utf-8')
    return path


class TestCheckServer:
    """Behaviour of check_server on a single server entry."""

    def test_valid_stdio_server_has_no_errors(self) -> None:
        assert check_server('playwright', {'command': 'npx', 'args': ['mcp']}) == []

    def test_non_object_entry_is_an_error(self) -> None:
        assert check_server('broken', 'npx mcp') == ['server `broken`: entry must be an object']

    def test_command_and_url_together_is_an_error(self) -> None:
        errors = check_server('both', {'command': 'npx', 'url': 'https://example.test/mcp'})
        assert errors == ['server `both`: declares both `command` and `url`; keep the one matching the transport']

    def test_neither_command_nor_url_is_an_error(self) -> None:
        errors = check_server('empty', {'type': 'stdio'})
        assert errors == ['server `empty`: declares neither `command` (stdio) nor `url` (remote)']

    def test_blank_command_is_an_error(self) -> None:
        assert check_server('blank', {'command': '  '}) == ['server `blank`: `command` must be a non-empty string']

    def test_stdio_transport_with_url_is_an_error(self) -> None:
        errors = check_server('remote', {'url': 'https://example.test/mcp', 'type': 'stdio'})
        assert errors == ['server `remote`: transport `stdio` contradicts `url` (expected http or sse)']

    def test_http_transport_with_command_is_an_error(self) -> None:
        errors = check_server('local', {'command': 'npx', 'transport': 'http'})
        assert errors == ['server `local`: transport `http` contradicts `command` (expected `stdio`)']

    def test_unknown_transport_is_an_error(self) -> None:
        errors = check_server('weird', {'url': 'https://example.test/mcp', 'type': 'grpc'})
        assert errors == ['server `weird`: unknown transport `grpc`']

    @pytest.mark.parametrize('transport', ['http', 'sse', 'streamable-http'])
    def test_known_remote_transports_are_accepted(self, transport: str) -> None:
        assert check_server('remote', {'url': 'https://example.test/mcp', 'type': transport}) == []

    def test_non_list_args_is_an_error(self) -> None:
        errors = check_server('bad', {'command': 'npx', 'args': 'mcp'})
        assert errors == ['server `bad`: `args` must be a list of strings']

    def test_non_string_args_entry_is_an_error(self) -> None:
        errors = check_server('bad', {'command': 'npx', 'args': ['mcp', 3]})
        assert errors == ['server `bad`: every `args` entry must be a string']

    def test_non_object_env_is_an_error(self) -> None:
        errors = check_server('bad', {'command': 'npx', 'env': ['A=1']})
        assert errors == ['server `bad`: `env` must be an object']

    def test_non_string_env_value_is_an_error(self) -> None:
        errors = check_server('bad', {'command': 'npx', 'env': {'PORT': 8080}})
        assert errors == ['server `bad`: `env.PORT` must be a string']

    def test_inlined_credential_is_an_error(self) -> None:
        server = {'command': 'npx', 'env': {'GITHUB_TOKEN': 'ghp_notarealtokenvalue'}}  # pragma: allowlist secret
        errors = check_server('github', server)
        assert errors == [
            'server `github`: `env.GITHUB_TOKEN` looks like an inlined credential; '
            'reference it as ${GITHUB_TOKEN} instead',
        ]

    def test_inlined_header_credential_is_an_error(self) -> None:
        server = {'url': 'https://example.test/mcp', 'headers': {'Authorization': 'Bearer abcdefghijklmnop'}}
        errors = check_server('remote', server)
        assert len(errors) == 1
        assert '`headers.Authorization` looks like an inlined credential' in errors[0]

    @pytest.mark.parametrize('value', ['${GITHUB_TOKEN}', '${GITHUB_TOKEN:-fallbackvalue}', 'short'])
    def test_referenced_or_short_credential_is_accepted(self, value: str) -> None:
        assert check_server('github', {'command': 'npx', 'env': {'GITHUB_TOKEN': value}}) == []

    def test_non_credential_key_is_not_flagged(self) -> None:
        server = {'command': 'npx', 'env': {'BASE_URL': 'https://example.test/api/v1'}}
        assert check_server('svc', server) == []


class TestCheckMcpConfig:
    """Behaviour of check_mcp_config on a whole configuration file."""

    def test_valid_config_has_no_errors(self, tmp_path: Path) -> None:
        assert check_mcp_config(_write(tmp_path, VALID)) == []

    def test_invalid_json_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / '.mcp.json'
        path.write_text('{"mcpServers": }', encoding='utf-8')
        errors = check_mcp_config(path)
        assert len(errors) == 1
        assert errors[0].startswith('invalid JSON:')

    def test_non_object_root_is_an_error(self, tmp_path: Path) -> None:
        assert check_mcp_config(_write(tmp_path, [])) == ['configuration root must be a JSON object']

    def test_missing_servers_key_is_an_error(self, tmp_path: Path) -> None:
        assert check_mcp_config(_write(tmp_path, {})) == ['missing `mcpServers` object: no server is registered']

    def test_non_object_servers_key_is_an_error(self, tmp_path: Path) -> None:
        errors = check_mcp_config(_write(tmp_path, {'mcpServers': []}))
        assert errors == ['`mcpServers` must be an object keyed by server name']

    def test_errors_are_collected_across_servers(self, tmp_path: Path) -> None:
        config = {'mcpServers': {'a': {}, 'b': {'command': 'npx', 'args': 'nope'}}}
        assert len(check_mcp_config(_write(tmp_path, config))) == 2


class TestClaudeMcpConfigMain:
    """Behaviour of the hook entry point."""

    def test_valid_config_returns_zero(self, tmp_path: Path) -> None:
        assert main([str(_write(tmp_path, VALID))]) == 0

    def test_invalid_config_returns_one(self, tmp_path: Path) -> None:
        assert main([str(_write(tmp_path, {'mcpServers': {'a': {}}}))]) == 1

    def test_missing_file_is_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / 'absent.json')]) == 0

    def test_error_is_reported_on_stderr(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = _write(tmp_path, {'mcpServers': {'a': {}}})
        assert main([str(path)]) == 1
        assert 'error: server `a`: declares neither' in capsys.readouterr().err

    def test_default_path_is_skipped_when_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0
