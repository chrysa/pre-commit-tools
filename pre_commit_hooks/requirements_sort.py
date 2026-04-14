#!/usr/bin/python3
"""Hook to sort requirements files and setup.cfg dependencies alphabetically."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools


def sort_requirements(lines: list[str]) -> list[str]:
    """Sort requirements lines: comments/blanks first, packages sorted case-insensitively."""
    comments = [line for line in lines if not line.strip() or line.strip().startswith('#')]
    packages = [line for line in lines if line.strip() and not line.strip().startswith('#')]
    sorted_packages = sorted(packages, key=_pkg_name_key)
    return comments + sorted_packages


def _collect_continuation(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect indented continuation lines starting at *start*.

    Returns ``(collected_lines, new_index)`` where *new_index* is the index of
    the first line that is not a continuation.
    """
    collected: list[str] = []
    i = start
    while i < len(lines) and lines[i].startswith((' ', '\t')):
        collected.append(lines[i])
        i += 1
    return collected, i


def _pkg_name_key(line: str) -> str:
    """Extract the package name from a dependency line for sorting.

    Strips version specifiers (``>=``, ``==``, etc.), extras (``[…]``) and
    inline comments so that sorting matches ``setup-cfg-fmt`` behaviour.
    """
    raw = line.strip().split('#')[0].strip()
    return re.split(r'[<>=!~;\[]', raw)[0].strip().lower()


def _sort_dep_block(dep_lines: list[str]) -> list[str]:
    """Sort dependency continuation lines by package name; trailing blank lines last."""
    blanks = [ln for ln in dep_lines if not ln.strip()]
    pkgs = [ln for ln in dep_lines if ln.strip()]
    pkgs.sort(key=_pkg_name_key)
    return pkgs + blanks


def sort_setup_cfg(content: str) -> str:
    """Sort ``install_requires`` and every ``extras_require`` block in a setup.cfg file.

    Keys in ``[options.extras_require]`` are sorted alphabetically and the
    dependencies within each key block are sorted case-insensitively.
    """
    lines = content.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    section = ''

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect section header -----------------------------------------------
        m = re.match(r'^\[([^\]]+)\]', stripped)
        if m:
            section = m.group(1)
            result.append(line)
            i += 1
            continue

        # [options] install_requires ------------------------------------------
        if section == 'options' and re.match(r'^install_requires\s*=', stripped):
            result.append(line)
            i += 1
            deps, i = _collect_continuation(lines, i)
            result.extend(_sort_dep_block(deps))
            continue

        # [options.extras_require] -------------------------------------------
        if section == 'options.extras_require':
            # Pass through blank/comment lines before any key block
            if not stripped or stripped.startswith('#'):
                result.append(line)
                i += 1
                continue

            # Collect all key=value blocks until the next section header
            blocks: list[tuple[str, list[str]]] = []
            while i < len(lines):
                ln = lines[i]
                s = ln.strip()
                if re.match(r'^\[([^\]]+)\]', s):
                    break
                # Skip blank/comment separators between key blocks
                if not s or s.startswith('#'):
                    i += 1
                    continue
                # Key line (non-indented)
                if not ln.startswith((' ', '\t')):
                    key_line = ln
                    i += 1
                    dep_lines, i = _collect_continuation(lines, i)
                    blocks.append((key_line, dep_lines))
                else:
                    # Orphan continuation — pass through unchanged
                    result.append(ln)
                    i += 1

            # Emit blocks sorted by key name
            blocks.sort(key=lambda b: b[0].split('=')[0].strip().lower())
            for key_line, dep_lines in blocks:
                result.append(key_line)
                result.extend(_sort_dep_block(dep_lines))
            # Preserve blank line separator before next section header
            if i < len(lines) and re.match(r'^\[([^\]]+)\]', lines[i].strip()):
                result.append('\n')
            continue

        result.append(line)
        i += 1

    return ''.join(result)


def main(argv: Sequence[str] | None = None) -> int:
    """Sort requirements files and setup.cfg; return 1 if any file was modified."""
    tools_instance = PreCommitTools()
    tools_instance.set_params(help_msg='sort requirements file or setup.cfg alphabetically')
    args, _ = tools_instance.get_args(argv=argv)
    changed = False
    for file in args.filenames:
        path = Path(file)
        original = path.read_text(encoding='utf-8')
        if path.name == 'setup.cfg':
            new_content = sort_setup_cfg(original)
        else:
            sorted_lines = sort_requirements(original.splitlines())
            new_content = '\n'.join(sorted_lines) + '\n'
        if new_content != original:
            path.write_text(new_content, encoding='utf-8')
            changed = True
    return int(changed)


if __name__ == '__main__':
    raise SystemExit(main())
