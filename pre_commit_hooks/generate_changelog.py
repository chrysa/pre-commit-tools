from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate CHANGELOG.md using git-cliff.",
    )
    parser.add_argument(
        "--output",
        default="CHANGELOG.md",
        dest="output",
        help="Path to the output changelog file (default: CHANGELOG.md)",
    )
    parser.add_argument(
        "--tag",
        default=None,
        dest="tag",
        help="Tag to use for the release (optional)",
    )
    parser.add_argument(
        "--unreleased",
        action="store_true",
        dest="unreleased",
        help="Only include unreleased commits",
    )
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    cmd = ["git", "cliff", "--output", args.output]
    if args.tag:
        cmd.extend(["--tag", args.tag])
    if args.unreleased:
        cmd.append("--unreleased")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    print(f"Changelog written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
