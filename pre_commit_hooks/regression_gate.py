#!/usr/bin/python3
"""Hook to detect metric regressions against a quality baseline.

Reads reports/coverage.xml and reports/test-results.xml (JUnit XML) produced
by ``make test``, then compares them against the values stored in
``.quality-baseline.json``.  Intended to run at the ``pre-push`` stage so
the developer is blocked before the push reaches CI.

Usage::

    # Check (default): block push if any metric regressed
    regression-gate

    # Write current metrics as the new baseline
    regression-gate --write-baseline

    # Override default paths
    regression-gate --coverage-report path/to/coverage.xml \
                    --test-report     path/to/junit.xml \
                    --baseline        path/to/.quality-baseline.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

_PRINT = print  # shadowed by print-detection hook — keep a reference


def _parse_coverage(report_path: Path) -> float | None:
    """Extract line-coverage percentage from a ``coverage.xml`` report."""
    if not report_path.exists():
        return None
    try:
        tree = ElementTree.parse(report_path)  # noqa: S314
        line_rate = tree.getroot().get('line-rate')
        if line_rate is not None:
            return round(float(line_rate) * 100, 2)
    except (ElementTree.ParseError, ValueError, OSError):
        pass
    return None


def _parse_test_count(report_path: Path) -> int | None:
    """Extract the number of passing tests from a JUnit XML report."""
    if not report_path.exists():
        return None
    try:
        tree = ElementTree.parse(report_path)  # noqa: S314
        root = tree.getroot()

        def _suite_passed(suite: ElementTree.Element) -> int:
            total = int(suite.get('tests', 0))
            errors = int(suite.get('errors', 0))
            failures = int(suite.get('failures', 0))
            return max(0, total - errors - failures)

        if root.tag == 'testsuite':
            return _suite_passed(root)

        suites = root.findall('testsuite')
        if suites:
            return sum(_suite_passed(s) for s in suites)

        # Fallback: count <testcase> elements that have no <failure>/<error>
        passed = sum(
            1 for tc in root.iter('testcase') if not (tc.find('failure') is not None or tc.find('error') is not None)
        )
        return passed
    except (ElementTree.ParseError, ValueError, OSError):
        pass
    return None


def _load_baseline(path: Path) -> dict | None:  # type: ignore[type-arg]
    """Return the baseline dict, or ``None`` if the file does not exist."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def _git_sha() -> str:
    """Return the short SHA of HEAD, or ``'unknown'``."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return 'unknown'


def _write_baseline(
    path: Path,
    coverage_pct: float | None,
    tests_passed: int | None,
) -> None:
    """Persist current metrics as the new baseline."""
    data: dict = {  # type: ignore[type-arg]
        '_comment': 'Regression baseline — update with: make baseline',
        'updated_at': datetime.now(tz=UTC).isoformat(),
        'git_sha': _git_sha(),
        'metrics': {
            'tests_passed': tests_passed if tests_passed is not None else 0,
            'coverage_pct': coverage_pct if coverage_pct is not None else 0.0,
        },
    }
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    _PRINT(  # print-detection: disable
        f'[regression-gate] Baseline written → '
        f'tests={data["metrics"]["tests_passed"]}, '
        f'coverage={data["metrics"]["coverage_pct"]}%',
    )


def _check(
    baseline_path: Path,
    coverage_path: Path,
    test_report_path: Path,
) -> int:
    """Compare current metrics against baseline. Return 0 (ok) or 1 (regression)."""
    baseline = _load_baseline(baseline_path)
    if baseline is None:
        _PRINT(  # print-detection: disable
            f"[regression-gate] No baseline at {baseline_path}. Run 'make baseline' to create one. Skipping check.",
        )
        return 0

    coverage_pct = _parse_coverage(coverage_path)
    tests_passed = _parse_test_count(test_report_path)
    regressions: list[str] = []
    metrics = baseline.get('metrics', {})

    # ── Coverage ──────────────────────────────────────────────────────────
    baseline_cov: float | None = metrics.get('coverage_pct')
    if coverage_pct is None:
        _PRINT(  # print-detection: disable
            f"[regression-gate] WARNING: {coverage_path} not found — run 'make test' first.",
        )
    elif baseline_cov is not None and coverage_pct < baseline_cov:
        delta = round(coverage_pct - baseline_cov, 2)
        regressions.append(
            f'  Coverage  : {coverage_pct}% < baseline {baseline_cov}%  (Δ {delta}%)',
        )

    # ── Test count ────────────────────────────────────────────────────────
    baseline_tests: int | None = metrics.get('tests_passed')
    if tests_passed is None:
        _PRINT(  # print-detection: disable
            f"[regression-gate] WARNING: {test_report_path} not found — run 'make test' first.",
        )
    elif baseline_tests is not None and tests_passed < baseline_tests:
        delta_t = tests_passed - baseline_tests
        regressions.append(
            f'  Tests     : {tests_passed} < baseline {baseline_tests}  (Δ {delta_t})',
        )

    if regressions:
        _PRINT('[regression-gate] REGRESSIONS DETECTED:')  # print-detection: disable
        for r in regressions:
            _PRINT(r)  # print-detection: disable
        _PRINT(  # print-detection: disable
            '\nFix the regressions before pushing, or update the baseline:\n  make baseline',
        )
        return 1

    cov_str = (
        f'{coverage_pct}% (baseline {baseline_cov}%)'
        if coverage_pct is not None and baseline_cov is not None
        else 'N/A'
    )
    tests_str = (
        f'{tests_passed} (baseline {baseline_tests})'
        if tests_passed is not None and baseline_tests is not None
        else 'N/A'
    )
    _PRINT(  # print-detection: disable
        f'[regression-gate] OK — coverage={cov_str}, tests={tests_str}',
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Regression gate: block push if quality metrics regressed.',
    )
    parser.add_argument(
        '--baseline',
        default='.quality-baseline.json',
        metavar='FILE',
        help='Baseline JSON file (default: .quality-baseline.json)',
    )
    parser.add_argument(
        '--coverage-report',
        default='reports/coverage.xml',
        metavar='FILE',
        help='Coverage XML report (default: reports/coverage.xml)',
    )
    parser.add_argument(
        '--test-report',
        default='reports/test-results.xml',
        metavar='FILE',
        help='JUnit test-results XML (default: reports/test-results.xml)',
    )
    parser.add_argument(
        '--write-baseline',
        action='store_true',
        help='Write current report metrics as the new baseline and exit 0',
    )
    args, _ = parser.parse_known_args(argv)

    baseline_path = Path(args.baseline)
    coverage_path = Path(args.coverage_report)
    test_report_path = Path(args.test_report)

    if args.write_baseline:
        _write_baseline(
            baseline_path,
            _parse_coverage(coverage_path),
            _parse_test_count(test_report_path),
        )
        return 0

    return _check(baseline_path, coverage_path, test_report_path)


if __name__ == '__main__':
    sys.exit(main())
