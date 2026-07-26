#!/usr/bin/python3
"""Hook to validate Claude Code MCP server configuration (``.mcp.json``).

An MCP server entry is either *stdio* (a ``command`` plus optional ``args``) or
remote (a ``url`` with an ``http``/``sse`` transport). Mixing both, or declaring
a transport that contradicts the keys present, yields a server that fails to
connect at session start with no actionable message.

The hook fails on: invalid JSON, a missing/malformed ``mcpServers`` mapping, a
server declaring neither or both of ``command``/``url``, a transport that
contradicts the declared keys, malformed ``args``/``env``/``headers``, and any
credential-looking value inlined instead of referenced as ``${VAR}``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ENV_REF_RE = re.compile(r'^\$\{[A-Za-z_]\w*(:-[^}]*)?\}$')
MIN_SECRET_LENGTH = 12
REMOTE_TRANSPORTS = frozenset({'http', 'sse', 'http-stream', 'streamable-http'})
SECRET_KEY_RE = re.compile(r'(api[_-]?key|auth|credential|password|secret|token)', re.IGNORECASE)
SERVERS_KEY = 'mcpServers'
STDIO_TRANSPORT = 'stdio'
TRANSPORT_KEYS = ('type', 'transport')


def _transport(server: dict[str, Any]) -> str | None:
    """Return the declared transport, whichever key carries it."""
    for key in TRANSPORT_KEYS:
        value = server.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _check_shape(name: str, server: dict[str, Any]) -> list[str]:
    """Return errors for the command/url/transport combination of one server."""
    has_command = 'command' in server
    has_url = 'url' in server
    if has_command and has_url:
        return [f'server `{name}`: declares both `command` and `url`; keep the one matching the transport']
    if not has_command and not has_url:
        return [f'server `{name}`: declares neither `command` (stdio) nor `url` (remote)']

    errors: list[str] = []
    key = 'command' if has_command else 'url'
    if not isinstance(server[key], str) or not server[key].strip():
        errors.append(f'server `{name}`: `{key}` must be a non-empty string')

    transport = _transport(server)
    if transport is None:
        return errors
    if has_command and transport != STDIO_TRANSPORT:
        errors.append(f'server `{name}`: transport `{transport}` contradicts `command` (expected `stdio`)')
    if has_url and transport == STDIO_TRANSPORT:
        errors.append(f'server `{name}`: transport `stdio` contradicts `url` (expected http or sse)')
    if has_url and transport not in REMOTE_TRANSPORTS and transport != STDIO_TRANSPORT:
        errors.append(f'server `{name}`: unknown transport `{transport}`')
    return errors


def _check_args(name: str, server: dict[str, Any]) -> list[str]:
    """Return errors for a malformed ``args`` list."""
    if 'args' not in server:
        return []
    args = server['args']
    if not isinstance(args, list):
        return [f'server `{name}`: `args` must be a list of strings']
    if any(not isinstance(item, str) for item in args):
        return [f'server `{name}`: every `args` entry must be a string']
    return []


def _check_string_map(name: str, server: dict[str, Any], key: str) -> list[str]:
    """Return errors for a mapping that must hold string values only."""
    if key not in server:
        return []
    mapping = server[key]
    if not isinstance(mapping, dict):
        return [f'server `{name}`: `{key}` must be an object']
    bad = sorted(entry for entry, value in mapping.items() if not isinstance(value, str))
    return [f'server `{name}`: `{key}.{entry}` must be a string' for entry in bad]


def _check_inline_secrets(name: str, server: dict[str, Any]) -> list[str]:
    """Return errors for credential values inlined instead of referenced as ``${VAR}``."""
    errors: list[str] = []
    for key in ('env', 'headers'):
        mapping = server.get(key)
        if not isinstance(mapping, dict):
            continue
        for entry, value in mapping.items():
            if not isinstance(value, str) or not SECRET_KEY_RE.search(entry):
                continue
            if ENV_REF_RE.fullmatch(value.strip()) or len(value.strip()) < MIN_SECRET_LENGTH:
                continue
            errors.append(
                f'server `{name}`: `{key}.{entry}` looks like an inlined credential; '
                f'reference it as ${{{entry.upper().replace("-", "_")}}} instead',
            )
    return errors


def check_server(name: str, server: Any) -> list[str]:
    """Return every error for a single MCP server entry."""
    if not isinstance(server, dict):
        return [f'server `{name}`: entry must be an object']
    errors = _check_shape(name, server)
    errors.extend(_check_args(name, server))
    for key in ('env', 'headers'):
        errors.extend(_check_string_map(name, server, key))
    errors.extend(_check_inline_secrets(name, server))
    return errors


def check_mcp_config(path: Path) -> list[str]:
    """Return every error for one MCP configuration file."""
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        return [f'invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})']

    if not isinstance(config, dict):
        return ['configuration root must be a JSON object']
    servers = config.get(SERVERS_KEY)
    if servers is None:
        return [f'missing `{SERVERS_KEY}` object: no server is registered']
    if not isinstance(servers, dict):
        return [f'`{SERVERS_KEY}` must be an object keyed by server name']

    errors: list[str] = []
    for name, server in servers.items():
        errors.extend(check_server(name, server))
    return errors


def main(argv: list[str] | None = None) -> int:
    """Validate every MCP configuration file passed on the command line."""
    parser = argparse.ArgumentParser(description='Validate Claude Code MCP server configuration')
    parser.add_argument('filenames', nargs='*', help='MCP config paths (default: ./.mcp.json)')
    args = parser.parse_args(argv)

    paths = [Path(name) for name in args.filenames] or [Path('.mcp.json')]
    retval = 0
    for path in paths:
        if not path.exists():
            continue
        errors = check_mcp_config(path)
        for error in errors:
            print(f'{path}: error: {error}', file=sys.stderr)
        if errors:
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
