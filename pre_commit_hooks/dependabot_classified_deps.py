#!/usr/bin/python3
"""Hook to keep the Dependabot config in sync with declared Python dependencies.

Every dependency declared in the project manifests (``setup.cfg``
``install_requires`` / ``extras_require`` and ``pyproject.toml`` PEP 621
dependencies) must be matched by a Dependabot group. Semantic groups (curated,
possibly glob-based) are owned by humans and never edited. One *managed* group
(``misc`` by default) is owned by the hook: it bidirectionally tracks every
declared package not matched by a semantic group — new packages are added,
removed packages are pruned, and the group is dropped entirely when empty
(Dependabot requires at least one pattern per group).

In the default *strict* mode the hook fails whenever the managed group is
non-empty, forcing the maintainer to reclassify those packages into a semantic
group. With ``--allow-unclassified`` the managed group is kept silently.
"""

from __future__ import annotations

import argparse
import configparser
import fnmatch
import io
import tomllib
from collections.abc import Sequence
from pathlib import Path

CATCH_ALL = '*'
DEFAULT_MANAGED_GROUP = 'misc'
_SPECIFIERS = ('==', '>=', '<=', '~=', '!=', '>', '<', '[', ';', ' ')


def _normalize(requirement: str) -> str | None:
    """Return the lower-cased distribution name from a requirement line."""
    line = requirement.split('#', 1)[0].strip()
    if not line:
        return None
    for specifier in _SPECIFIERS:
        line = line.split(specifier, 1)[0]
    return line.strip().lower() or None


def _packages_from_setup_cfg(path: Path) -> set[str]:
    """Collect names from install_requires and every extras_require group."""
    if not path.exists():
        return set()
    parser = configparser.ConfigParser()
    parser.read(path, encoding='utf-8')
    raw: list[str] = []
    if parser.has_option('options', 'install_requires'):
        raw += parser.get('options', 'install_requires').splitlines()
    if parser.has_section('options.extras_require'):
        for _, value in parser.items('options.extras_require'):
            raw += value.splitlines()
    return {name for line in raw if (name := _normalize(line))}


def _packages_from_pyproject(path: Path) -> set[str]:
    """Collect PEP 621 dependencies and optional-dependencies from pyproject.toml."""
    if not path.exists():
        return set()
    project = tomllib.loads(path.read_text(encoding='utf-8')).get('project', {})
    raw: list[str] = list(project.get('dependencies', []))
    for group in project.get('optional-dependencies', {}).values():
        raw += group
    return {name for line in raw if (name := _normalize(line))}


def _declared_packages(manifests: Sequence[Path]) -> set[str]:
    """Merge declared package names across every supported manifest."""
    packages: set[str] = set()
    for manifest in manifests:
        if manifest.name == 'setup.cfg':
            packages |= _packages_from_setup_cfg(manifest)
        elif manifest.name == 'pyproject.toml':
            packages |= _packages_from_pyproject(manifest)
    return packages


def _pip_update(config: dict, ecosystem: str) -> dict | None:
    """Return the updates entry for the given ecosystem, or None."""
    for update in config.get('updates', []):
        if update.get('package-ecosystem') == ecosystem:
            return update
    return None


def _semantic_patterns(update: dict, managed_group: str) -> list[str]:
    """Return patterns from every group except the managed one and the catch-all."""
    patterns: list[str] = []
    for name, group in update.get('groups', {}).items():
        if name == managed_group:
            continue
        patterns += [p.lower() for p in group.get('patterns', []) if p != CATCH_ALL]
    return patterns


def _unclassified(packages: set[str], patterns: Sequence[str]) -> list[str]:
    """Return sorted packages not matched by any semantic group pattern."""
    return sorted(pkg for pkg in packages if not any(fnmatch.fnmatch(pkg, pattern) for pattern in patterns))


def _apply_managed_group(update: dict, managed_group: str, packages: list[str]) -> bool:
    """Sync the managed group to ``packages``; return True if the config changed."""
    from ruamel.yaml.comments import CommentedMap

    groups = update.setdefault('groups', CommentedMap())
    current = list(groups[managed_group]['patterns']) if managed_group in groups else None
    desired = packages or None
    if current == desired:
        return False
    if desired is None:
        del groups[managed_group]
    else:
        groups[managed_group] = CommentedMap(patterns=list(desired))
    return True


def sync(
    dependabot_path: Path,
    manifests: Sequence[Path],
    ecosystem: str = 'pip',
    managed_group: str = DEFAULT_MANAGED_GROUP,
) -> tuple[list[str], bool]:
    """Sync the managed group with declared deps; return (unclassified, changed)."""
    if not dependabot_path.exists():
        return [], False
    from ruamel.yaml import YAML

    raw = dependabot_path.read_text(encoding='utf-8')
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.explicit_start = raw.lstrip().startswith('---')
    yaml.indent(mapping=4, sequence=6, offset=4)
    config = yaml.load(raw) or {}
    update = _pip_update(config, ecosystem)
    if update is None:
        return [], False
    unclassified = _unclassified(
        _declared_packages(manifests),
        _semantic_patterns(update, managed_group),
    )
    changed = _apply_managed_group(update, managed_group, unclassified)
    if changed:
        buffer = io.StringIO()
        yaml.dump(config, buffer)
        dependabot_path.write_text(buffer.getvalue(), encoding='utf-8')
    return unclassified, changed


def _report(path: Path, group: str, unclassified: list[str], changed: bool) -> None:
    """Print a human-readable summary of the sync outcome."""
    if changed:
        print(f'{path}: managed {group!r} group synced with declared dependencies.')
    if unclassified:
        print(f'Dependencies parked in the {group!r} managed group (please reclassify):')
        for orphan in unclassified:
            print(f'  - {orphan}')


def main(argv: Sequence[str] | None = None) -> int:
    """Sync Dependabot groups; fail on managed changes or unclassified deps."""
    parser = argparse.ArgumentParser(
        description='Sync Dependabot groups with declared Python dependencies',
    )
    parser.add_argument('filenames', nargs='*', help='manifest files (unused as input)')
    parser.add_argument('--dependabot', default='.github/dependabot.yml')
    parser.add_argument('--manifest', action='append', default=None)
    parser.add_argument('--ecosystem', default='pip')
    parser.add_argument('--managed-group', default=DEFAULT_MANAGED_GROUP)
    parser.add_argument(
        '--allow-unclassified',
        action='store_true',
        help='keep packages in the managed group without failing',
    )
    args = parser.parse_args(argv)

    manifests = [Path(name) for name in (args.manifest or ['setup.cfg', 'pyproject.toml'])]
    path = Path(args.dependabot)
    unclassified, changed = sync(path, manifests, args.ecosystem, args.managed_group)
    _report(path, args.managed_group, unclassified, changed)
    if changed:
        return 1
    if unclassified and not args.allow_unclassified:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
