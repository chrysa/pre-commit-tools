#!/usr/bin/python3
"""Hook to validate syntax of JavaScript and Google Apps Script (.gs) files using Node.js."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

Violation = tuple[str, str]


def _check_node_available() -> bool:
    """Return True if node is available in PATH."""
    try:
        subprocess.run(
            ['node', '--version'],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    else:
        return True


def _check_via_temp_js(filename: str) -> list[Violation]:
    """Check .gs file by copying to a temp .js file (Node.js 24 workaround).

    Node.js 24 raises ERR_UNKNOWN_FILE_EXTENSION for .gs files because it
    enforces ES module resolution by extension. Copying to a .js temporary
    file bypasses this restriction without changing the syntax being checked.
    """
    source = Path(filename).read_bytes()
    with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tmp:
        tmp.write(source)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ['node', '--check', tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return [(filename, f'node check failed: {exc}')]
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip().replace(tmp_path, filename)
        return [(filename, error)]
    return []


def check_syntax(filename: str) -> list[Violation]:
    """Run node --check on the file and return list of (filename, error_message)."""
    # Node.js 24+ raises ERR_UNKNOWN_FILE_EXTENSION for .gs files.
    # Use a temp .js file to bypass this limitation.
    if Path(filename).suffix == '.gs':
        return _check_via_temp_js(filename)
    try:
        result = subprocess.run(
            ['node', '--check', filename],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return [(filename, f'node check failed: {exc}')]
    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip()
        return [(filename, error)]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    """Check JavaScript/.gs files for syntax errors using Node.js."""
    tools = PreCommitTools()
    tools.set_params(help_msg='validate JS/.gs syntax with node --check')
    args, _ = tools.get_args(argv=argv)

    if not _check_node_available():
        print('js-syntax-check: node not found in PATH, skipping syntax check', file=sys.stderr)
        return 0

    retval = 0
    for filename in args.filenames:
        if not Path(filename).exists():
            continue
        for fname, msg in check_syntax(filename):
            print(f'{fname}: syntax error\n{msg}', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
