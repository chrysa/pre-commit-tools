#!/usr/bin/python3
"""Safe reader for the file paths a hook receives on its command line.

pre-commit passes staged paths, but a hook is also invoked by hand and by agents,
so a path argument is untrusted input: `../../etc/shadow` or an absolute path
outside the project must not be read just because it was typed. Every read goes
through :func:`read_source`, which resolves the path and refuses anything that
escapes the working tree.
"""

from __future__ import annotations

from pathlib import Path


def read_source(filename: str, root: Path | None = None) -> str | None:
    """Return the text of `filename` when it resolves inside `root`, else None.

    `root` defaults to the current working directory — the repository root, as
    pre-commit always runs hooks from there. Unreadable, missing, non-UTF-8 and
    out-of-tree paths all yield None so the caller simply skips the file.
    """
    base = (root or Path.cwd()).resolve()
    try:
        candidate = Path(filename).resolve()
    except (OSError, RuntimeError):  # unresolvable path (broken symlink loop, …)
        return None
    if not candidate.is_relative_to(base):
        return None
    try:
        return candidate.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
