#!/usr/bin/python3
"""Hook to detect compose dev services that cannot hot-reload.

Enforces the shared-standards rule *Dev stage must hot-reload*: a ``dev`` service
whose source is baked into the image reflects an edit only after a rebuild, which
makes it a production image wearing a dev label. The check is static — it verifies
that the service declares a way for host source to reach the container, either a
bind mount or a compose ``develop.watch`` sync action.
"""

from __future__ import annotations

from collections.abc import Sequence

_DISABLE_COMMENT = '# compose-dev-hot-reload: disable'
_DEFAULT_TARGETS = ('dev', 'development')
_SYNC_ACTIONS = frozenset({'sync', 'sync+restart', 'sync+exec'})

Violation = tuple[str, int, str]


def _is_dev_service(name: str, service: dict, targets: Sequence[str]) -> bool:
    """Return True when the service builds (or is named after) a dev target."""
    wanted = {t.lower() for t in targets}
    build = service.get('build')
    if isinstance(build, dict):
        target = build.get('target')
        if isinstance(target, str) and target.lower() in wanted:
            return True
    lowered = name.lower()
    return lowered in wanted or any(lowered.endswith(f'-{t}') for t in wanted)


def _has_bind_mount(service: dict) -> bool:
    """Return True when a host path is mounted into the container.

    Both compose syntaxes count: the short form (``./src:/code``, ``.:/code``) and
    the long form (``type: bind``). A named volume is not a source mount — it
    shadows the tree instead of exposing it.
    """
    volumes = service.get('volumes')
    if not isinstance(volumes, list):
        return False
    for volume in volumes:
        if isinstance(volume, dict):
            if volume.get('type') == 'bind':
                return True
            continue
        if not isinstance(volume, str):
            continue
        source = volume.split(':', 1)[0].strip()
        if source.startswith(('.', '/', '~', '$')):
            return True
    return False


def _has_watch_sync(service: dict) -> bool:
    """Return True when ``develop.watch`` declares a sync action."""
    develop = service.get('develop')
    if not isinstance(develop, dict):
        return False
    watch = develop.get('watch')
    if not isinstance(watch, list):
        return False
    return any(isinstance(entry, dict) and str(entry.get('action', '')).lower() in _SYNC_ACTIONS for entry in watch)


def detect_dev_without_hot_reload(
    source: str,
    filename: str,
    targets: Sequence[str] = _DEFAULT_TARGETS,
) -> list[Violation]:
    """Return violations for dev services with no path from host source to container."""
    if _DISABLE_COMMENT in source:
        return []

    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError

    try:
        document = YAML(typ='safe').load(source)
    except YAMLError:
        return []
    if not isinstance(document, dict):
        return []
    services = document.get('services')
    if not isinstance(services, dict):
        return []

    violations: list[Violation] = []
    for name, service in services.items():
        if not isinstance(service, dict):
            continue
        if not _is_dev_service(str(name), service, targets):
            continue
        if _has_bind_mount(service) or _has_watch_sync(service):
            continue
        violations.append(
            (
                filename,
                1,
                f"service '{name}' targets a dev build but mounts no source and declares no "
                'develop.watch sync; a source edit needs a rebuild, so it cannot hot-reload',
            ),
        )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Detect compose dev services that cannot hot-reload and return 1 if any found."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect compose dev services that cannot hot-reload',
    )
    parser.add_argument('filenames', nargs='*')
    parser.add_argument(
        '--target',
        action='append',
        default=None,
        metavar='NAME',
        help='Build target treated as a dev service. Repeatable; defaults to dev and development.',
    )
    args = parser.parse_args(argv)

    targets = args.target or list(_DEFAULT_TARGETS)
    retval = 0
    for filename in args.filenames:
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for fname, lineno, msg in detect_dev_without_hot_reload(source, filename, targets):
            print(f'{fname}:{lineno}: {msg}')
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
