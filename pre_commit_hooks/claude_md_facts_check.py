#!/usr/bin/python3
"""Hook to validate a CLAUDE.md / AGENTS.md file's factual claims against the repo.

Unlike ``copilot_instructions_duplication`` (doc-vs-doc) or ``guideline_checker``
(code-vs-rules), this hook checks that the *verifiable factual claims* a
CLAUDE.md / AGENTS.md makes about its own repository still match reality on
disk.  It is deterministic: no LLM, no network — it only reads files.

Only claim types that can be parsed with confidence are checked; anything
ambiguous is skipped rather than invented as a violation.  Checked claims:

1. Language/stack — a doc that asserts a primary language with neither a
   matching manifest nor matching sources on disk.
2. Python version — a stated ``Python 3.x`` that disagrees with pyproject's
   ``requires-python`` minor.
3. Make targets — a documented ``make <target>`` absent from the repo Makefile
   and every included ``*.Makefile`` / ``*.makefile`` / ``*.mk`` fragment. A
   target named only as a negated counter-example ("never ``make X``") is ignored.
4. Project name — a code-span package name that differs from pyproject /
   package.json (WARN, promoted to FAIL only with ``--strict``).

Usage::

    claude-md-facts-check CLAUDE.md AGENTS.md
    claude-md-facts-check --strict CLAUDE.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Sequence
from pathlib import Path

_DISABLE_COMMENT = 'claude-md-facts-check: disable'

# Vendored / hidden directories never contain a repo's own targets or sources; pruned
# from every tree walk for both speed and correctness.
_MAKEFILE_PRUNE_DIRS = frozenset({'.git', 'node_modules', '.venv', 'venv', '__pycache__'})

_PYTHON_MANIFESTS = ('pyproject.toml', 'setup.py')
_JS_MANIFESTS = ('package.json',)
_PYTHON_SUFFIXES = ('.py',)
_JS_SUFFIXES = ('.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs')

# A language claim only fires when the doc names the language as the stack.
_STACK_KEYWORDS: dict[str, tuple[str, ...]] = {
    'Python': ('python', 'django', 'fastapi', 'flask'),
    'JavaScript/TypeScript': ('typescript', 'javascript', 'node.js', 'react', 'vue'),
}
_STACK_MANIFESTS: dict[str, tuple[str, ...]] = {
    'Python': _PYTHON_MANIFESTS,
    'JavaScript/TypeScript': _JS_MANIFESTS,
}
_STACK_SUFFIXES: dict[str, tuple[str, ...]] = {
    'Python': _PYTHON_SUFFIXES,
    'JavaScript/TypeScript': _JS_SUFFIXES,
}

_PY_VERSION_RE = re.compile(r'Python\s+3\.(\d+)')
_REQUIRES_PYTHON_RE = re.compile(r'requires-python\s*=\s*["\'][^"\']*?3\.(\d+)')
# ``make target`` — code span REQUIRED on both sides so English prose
# ("make sure", "make targets") is never mistaken for a real target.
_MAKE_TARGET_RE = re.compile(r'`make\s+([A-Za-z0-9][A-Za-z0-9_.-]*)`')
# A line that names ``make X`` only to say it is *wrong* (a counter-example) must
# not be read as documenting that target. Cue words appearing on the same line
# suppress the finding, e.g. "no `make type-check` when the target is `typecheck`"
# or "use `make typecheck`, never `make type-check`".
_NEGATION_CUE_RE = re.compile(
    r'\b(?:no|not|never|instead of|rather than|avoid|don\'?t|wrong|incorrect|mistake|typo)\b',
    re.IGNORECASE,
)
_MAKEFILE_TARGET_RE = re.compile(r'^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)', re.MULTILINE)
# A code-spanned project name, e.g. `my-package`.
_CODE_SPAN_RE = re.compile(r'`([A-Za-z0-9][A-Za-z0-9_.-]{1,63})`')


class Finding:
    """A single check result: a FAIL (hard) or a WARN (soft)."""

    def __init__(self, message: str, *, warn: bool = False) -> None:
        self.message = message
        self.warn = warn


def resolve_repo_root(doc_file: Path) -> Path:
    """Return the repo root for *doc_file*.

    The root is the directory holding the doc, or its parent when the doc lives
    under a ``.claude/`` directory (``.claude/CLAUDE.md`` describes the repo).
    """
    parent = doc_file.resolve().parent
    if parent.name == '.claude':
        return parent.parent
    return parent


def _has_manifest(repo_root: Path, manifests: Sequence[str]) -> bool:
    return any((repo_root / manifest).exists() for manifest in manifests)


def _has_sources(repo_root: Path, suffixes: Sequence[str]) -> bool:
    """True if any file with one of *suffixes* exists, ignoring vendored/hidden trees.

    Uses os.walk with in-place dir pruning (rather than rglob) so a large repo with a
    heavy .git / node_modules / .venv is not walked in full, and stops at the first hit.
    """
    wanted = tuple(suffixes)
    for _dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _MAKEFILE_PRUNE_DIRS and not d.startswith('.')]
        if any(name.endswith(wanted) for name in filenames):
            return True
    return False


def check_stack_claim(text: str, repo_root: Path) -> Finding | None:
    """Flag a stack the doc names that has neither a manifest nor sources."""
    lowered = text.lower()
    for language, keywords in _STACK_KEYWORDS.items():
        if not any(keyword in lowered for keyword in keywords):
            continue
        if _has_manifest(repo_root, _STACK_MANIFESTS[language]):
            continue
        if _has_sources(repo_root, _STACK_SUFFIXES[language]):
            continue
        return Finding(
            f'claims {language} but no {language} manifest/sources found in {repo_root}',
        )
    return None


def _requires_python_minor(repo_root: Path) -> int | None:
    """Return the ``requires-python`` minor from pyproject, or None."""
    pyproject = repo_root / 'pyproject.toml'
    if not pyproject.exists():
        return None
    match = _REQUIRES_PYTHON_RE.search(pyproject.read_text(encoding='utf-8'))
    return int(match.group(1)) if match else None


def check_python_version(text: str, repo_root: Path) -> Finding | None:
    """Flag a stated ``Python 3.x`` that disagrees with pyproject's minor."""
    doc_match = _PY_VERSION_RE.search(text)
    if doc_match is None:
        return None
    pyproject_minor = _requires_python_minor(repo_root)
    if pyproject_minor is None:
        return None
    doc_minor = int(doc_match.group(1))
    if doc_minor == pyproject_minor:
        return None
    return Finding(
        f'doc states Python 3.{doc_minor} but pyproject requires-python is 3.{pyproject_minor}',
    )


def _iter_makefile_sources(repo_root: Path) -> list[Path]:
    """Return every file whose targets count as reachable from ``Makefile``.

    Covers the root ``Makefile``, ``makefiles/*.mk``, and — because chrysa Makefiles
    routinely pull them in via ``include $(shell find … -name '*.[Mm]akefile')`` or
    ``include $(wildcard *.Makefile)`` — every ``*.Makefile`` / ``*.makefile`` /
    ``*.mk`` in the tree (hidden and vendored directories pruned). Rather than parse
    the ``include`` directive, resolve the same file set the glob would, so targets
    living in an included fragment are not reported as missing.
    """
    sources = [repo_root / 'Makefile']
    # os.walk with in-place dir pruning skips vendored/hidden trees before descending
    # (rglob would still walk into them), which keeps this fast on large repos.
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _MAKEFILE_PRUNE_DIRS and not d.startswith('.')]
        sources.extend(
            Path(dirpath) / filename for filename in filenames if filename.endswith(('.Makefile', '.makefile', '.mk'))
        )
    return sources


def _makefile_targets(repo_root: Path) -> set[str]:
    """Return every target declared in the Makefile and its included fragments."""
    targets: set[str] = set()
    for source in _iter_makefile_sources(repo_root):
        if not source.exists():
            continue
        targets.update(_MAKEFILE_TARGET_RE.findall(source.read_text(encoding='utf-8')))
    return targets


def check_make_targets(text: str, repo_root: Path) -> list[Finding]:
    """Flag documented ``make <target>`` calls absent from the Makefile.

    A ``make X`` code-span whose line also carries a negation cue (e.g. "never
    ``make type-check``", "no ``make foo`` — the target is ``bar``") names the
    target only as a counter-example, so it is not treated as documenting it.
    """
    if not (repo_root / 'Makefile').exists():
        return []
    known = _makefile_targets(repo_root)
    findings: list[Finding] = []
    seen: set[str] = set()
    for line in text.splitlines():
        negated = _NEGATION_CUE_RE.search(line) is not None
        for target in _MAKE_TARGET_RE.findall(line):
            if target in seen:
                continue
            if target in known:
                seen.add(target)  # real target: never report, and don't let a later
                continue  # negated-only line resurrect it
            if negated:
                continue  # counter-example mention, not documentation
            seen.add(target)
            findings.append(Finding(f'documented `make {target}` not found in Makefile'))
    return findings


def _declared_project_name(repo_root: Path) -> str | None:
    """Return the pyproject/package.json declared name, or None."""
    pyproject = repo_root / 'pyproject.toml'
    if pyproject.exists():
        match = re.search(
            r'^\s*name\s*=\s*["\']([^"\']+)["\']',
            pyproject.read_text(encoding='utf-8'),
            re.MULTILINE,
        )
        if match:
            return match.group(1)
    package_json = repo_root / 'package.json'
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            return None
        name = data.get('name')
        if isinstance(name, str) and name:
            return name
    return None


def check_project_name(text: str, repo_root: Path) -> Finding | None:
    """Warn when a declared package name never appears in a doc code-span."""
    declared = _declared_project_name(repo_root)
    if declared is None:
        return None
    code_spans = set(_CODE_SPAN_RE.findall(text))
    if not code_spans:
        return None
    if declared in code_spans:
        return None
    return Finding(
        f'doc code-spans name a package other than declared `{declared}` (pyproject/package.json)',
        warn=True,
    )


def collect_findings(doc_file: Path, text: str, repo_root: Path) -> list[Finding]:
    """Run every check for a single doc and return its findings."""
    findings: list[Finding] = []
    if (stack := check_stack_claim(text, repo_root)) is not None:
        findings.append(stack)
    if (python_version := check_python_version(text, repo_root)) is not None:
        findings.append(python_version)
    findings.extend(check_make_targets(text, repo_root))
    if (name := check_project_name(text, repo_root)) is not None:
        findings.append(name)
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    """Validate CLAUDE.md / AGENTS.md factual claims; return 1 on any hard fail."""
    parser = argparse.ArgumentParser(
        description="Validate a CLAUDE.md/AGENTS.md's factual claims against the repo on disk",
    )
    parser.add_argument('filenames', nargs='*', help='CLAUDE.md/AGENTS.md files passed by pre-commit')
    parser.add_argument(
        '--strict',
        action='store_true',
        help='also fail on WARN-level findings (e.g. project-name drift)',
    )
    args = parser.parse_args(argv)

    ret_val = 0
    for filename in args.filenames:
        doc_file = Path(filename)
        if not doc_file.exists():
            continue

        text = doc_file.read_text(encoding='utf-8')
        if _DISABLE_COMMENT in text:
            continue

        repo_root = resolve_repo_root(doc_file)
        findings = collect_findings(doc_file, text, repo_root)
        for finding in findings:
            fails = not finding.warn or args.strict
            level = 'FAIL' if fails else 'WARN'
            print(  # print-detection: disable
                f'[claude-md-facts-check] {level} {doc_file}: {finding.message}',
            )
            if fails:
                ret_val = 1

    return ret_val


if __name__ == '__main__':
    raise SystemExit(main())
