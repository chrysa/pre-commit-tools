#!/usr/bin/python3
"""Hook to run helm lint --strict on Helm charts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _find_charts(search_root: Path) -> list[Path]:
    """Return chart directories at <root>/<namespace>/<service>/."""
    charts: list[Path] = []
    if not search_root.exists():
        return charts
    for ns_dir in search_root.iterdir():
        if not ns_dir.is_dir():
            continue
        for svc_dir in ns_dir.iterdir():
            if svc_dir.is_dir() and (svc_dir / 'Chart.yaml').exists():
                charts.append(svc_dir)
    return charts


def main(argv: list[str] | None = None) -> int:
    """Run helm lint --strict on every chart directory found under charts/."""
    parser = argparse.ArgumentParser(description='Run helm lint --strict on Helm charts')
    parser.add_argument(
        '--charts-dir',
        default='charts',
        help='root directory containing <namespace>/<service> chart dirs (default: charts)',
    )
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    if shutil.which('helm') is None:
        print('helm-lint: helm not found in PATH — skipping', file=sys.stderr)
        return 0

    charts_root = Path(args.charts_dir)
    charts = _find_charts(charts_root)
    if not charts:
        return 0

    retval = 0
    for chart in sorted(charts):
        result = subprocess.run(
            ['helm', 'lint', str(chart), '--strict'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(result.stdout, end='')
            print(result.stderr, end='', file=sys.stderr)
            retval = 1
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
