#!/usr/bin/python3
"""Hook to detect dead/unused code using vulture."""

from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run vulture to detect unused code and return 1 if any is found."""
    try:
        import vulture as _vulture
    except ImportError:
        print(
            'vulture is required: pip install vulture  (or add it to additional_dependencies)',
        )  # print-detection: disable
        return 1

    from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

    tools_instance = PreCommitTools()
    tools_instance.set_params(
        help_msg='detect dead/unused code using vulture',
        arguments=[
            (
                '--min-confidence',
                {
                    'type': int,
                    'default': 80,
                    'help': 'Minimum confidence percentage for unused code reports (default: 80)',
                },
            ),
            (
                '--exclude',
                {
                    'nargs': '*',
                    'default': [],
                    'metavar': 'PATTERN',
                    'help': 'Glob patterns of paths to exclude (e.g. tests/ migrations/)',
                },
            ),
            (
                '--whitelist',
                {
                    'nargs': '*',
                    'default': [],
                    'metavar': 'FILE',
                    'help': 'Vulture whitelist Python files listing used names to suppress false positives',
                },
            ),
        ],
    )
    args, _ = tools_instance.get_args(argv=argv)

    v = _vulture.Vulture()
    paths = list(args.whitelist) + [str(p) for p in args.filenames]
    v.scavenge(paths, exclude=args.exclude or [])
    unused = list(v.get_unused_code(min_confidence=args.min_confidence))
    for item in unused:
        print(
            f'[{item.filename}:{item.first_lineno}] unused {item.typ}: {item.name}',
        )  # print-detection: disable
    return int(bool(unused))


if __name__ == '__main__':
    raise SystemExit(main())
