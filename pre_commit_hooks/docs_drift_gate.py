#!/usr/bin/python3
"""Hook to keep generated docs in sync with the code.

Regenerates code-derived docs via a make target, then fails if the working
tree drifts from the committed copy.  Intended to run at the ``pre-push`` stage
so the developer is blocked before the push reaches CI.

The consuming repo owns the generators behind ``make <target>`` (default
``docs-code``); this hook only enforces the diff.  Keep the generators
deterministic (sorted output, pinned hashes) so the check stays quiet.

Usage::

    docs-drift-gate                              # make docs-code + git diff -- docs/
    docs-drift-gate --target docs --paths docs/ public/
"""

from __future__ import annotations

import argparse
import subprocess
import sys

_PRINT = print  # shadowed by print-detection hook — keep a reference


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _regenerate(target: str) -> int:
    """Run ``make <target>``. Return its exit code (0 on success)."""
    result = _run(['make', target])
    if result.returncode != 0:
        _PRINT(  # print-detection: disable
            f"[docs-drift-gate] 'make {target}' failed:\n{result.stderr.strip()}",
        )
    return result.returncode


def _diff(paths: list[str]) -> int:
    """Fail (1) if the working tree drifts from the committed docs."""
    result = _run(['git', 'diff', '--exit-code', '--', *paths])
    if result.returncode == 0:
        _PRINT(  # print-detection: disable
            f'[docs-drift-gate] OK — docs match the code ({" ".join(paths)}).',
        )
        return 0
    stat = _run(['git', 'diff', '--stat', '--', *paths]).stdout.strip()
    _PRINT(  # print-detection: disable
        f'[docs-drift-gate] Generated docs are stale:\n{stat}\n\nRegenerate and commit them (e.g. `make docs`).',
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Docs drift gate: regenerate code-derived docs and block push on drift.',
    )
    parser.add_argument(
        '--target',
        default='docs-code',
        metavar='MAKE_TARGET',
        help='Make target that regenerates code-derived docs (default: docs-code)',
    )
    parser.add_argument(
        '--paths',
        nargs='+',
        default=['docs/'],
        metavar='PATH',
        help='Paths the drift check inspects (default: docs/)',
    )
    args, _ = parser.parse_known_args(argv)

    if _regenerate(args.target) != 0:
        return 1
    return _diff(args.paths)


if __name__ == '__main__':
    sys.exit(main())
