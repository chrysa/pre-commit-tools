"""Tests for regression_gate hook."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pre_commit_hooks.regression_gate import (
    _check,
    _load_baseline,
    _parse_coverage,
    _parse_test_count,
    _write_baseline,
    main,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

COVERAGE_XML_85 = """\
<?xml version="1.0" ?>
<coverage version="7.0" line-rate="0.85" branch-rate="0.80" timestamp="1234567890">
    <packages/>
</coverage>
"""

COVERAGE_XML_90 = """\
<?xml version="1.0" ?>
<coverage version="7.0" line-rate="0.90" branch-rate="0.85" timestamp="1234567890">
    <packages/>
</coverage>
"""

JUNIT_XML_10_PASS = """\
<?xml version="1.0" ?>
<testsuites>
    <testsuite tests="10" errors="0" failures="0" name="suite"/>
</testsuites>
"""

JUNIT_XML_8_PASS = """\
<?xml version="1.0" ?>
<testsuites>
    <testsuite tests="10" errors="1" failures="1" name="suite"/>
</testsuites>
"""

JUNIT_XML_SINGLE_SUITE = """\
<?xml version="1.0" ?>
<testsuite tests="5" errors="0" failures="0" name="suite"/>
"""


def _baseline(tests: int, coverage: float) -> dict:  # type: ignore[type-arg]
    return {
        '_comment': 'test',
        'updated_at': '2026-01-01T00:00:00+00:00',
        'git_sha': 'abc123',
        'metrics': {'tests_passed': tests, 'coverage_pct': coverage},
    }


# ─────────────────────────────────────────────────────────────────────────────
# _parse_coverage
# ─────────────────────────────────────────────────────────────────────────────


class TestParseCoverage:
    def test_parses_line_rate_correctly(self, tmp_path: Path) -> None:
        f = tmp_path / 'coverage.xml'
        f.write_text(COVERAGE_XML_85)
        assert _parse_coverage(f) == 85.0

    def test_parses_90_percent(self, tmp_path: Path) -> None:
        f = tmp_path / 'coverage.xml'
        f.write_text(COVERAGE_XML_90)
        assert _parse_coverage(f) == 90.0

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _parse_coverage(tmp_path / 'nope.xml') is None

    def test_malformed_xml_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / 'bad.xml'
        f.write_text('not xml at all')
        assert _parse_coverage(f) is None

    def test_missing_line_rate_attribute_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / 'coverage.xml'
        f.write_text('<coverage version="7.0"><packages/></coverage>')
        assert _parse_coverage(f) is None


# ─────────────────────────────────────────────────────────────────────────────
# _parse_test_count
# ─────────────────────────────────────────────────────────────────────────────


class TestParseTestCount:
    def test_counts_passing_tests_in_testsuites(self, tmp_path: Path) -> None:
        f = tmp_path / 'results.xml'
        f.write_text(JUNIT_XML_10_PASS)
        assert _parse_test_count(f) == 10

    def test_subtracts_errors_and_failures(self, tmp_path: Path) -> None:
        f = tmp_path / 'results.xml'
        f.write_text(JUNIT_XML_8_PASS)
        assert _parse_test_count(f) == 8

    def test_single_testsuite_root(self, tmp_path: Path) -> None:
        f = tmp_path / 'results.xml'
        f.write_text(JUNIT_XML_SINGLE_SUITE)
        assert _parse_test_count(f) == 5

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _parse_test_count(Path('/non/existent/file.xml')) is None

    def test_malformed_xml_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / 'bad.xml'
        f.write_text('definitely not xml')
        assert _parse_test_count(f) is None

    def test_multiple_testsuites_summed(self, tmp_path: Path) -> None:
        xml = """\
<?xml version="1.0" ?>
<testsuites>
    <testsuite tests="4" errors="0" failures="0" name="a"/>
    <testsuite tests="6" errors="0" failures="1" name="b"/>
</testsuites>
"""
        f = tmp_path / 'results.xml'
        f.write_text(xml)
        assert _parse_test_count(f) == 9


# ─────────────────────────────────────────────────────────────────────────────
# _load_baseline
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadBaseline:
    def test_returns_dict_for_valid_file(self, tmp_path: Path) -> None:
        f = tmp_path / '.quality-baseline.json'
        f.write_text(json.dumps(_baseline(10, 85.0)))
        result = _load_baseline(f)
        assert result is not None
        assert result['metrics']['tests_passed'] == 10

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert _load_baseline(tmp_path / 'nope.json') is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / 'bad.json'
        f.write_text('{broken json')
        assert _load_baseline(f) is None


# ─────────────────────────────────────────────────────────────────────────────
# _write_baseline
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteBaseline:
    def test_creates_file_with_metrics(self, tmp_path: Path) -> None:
        f = tmp_path / '.quality-baseline.json'
        with patch('pre_commit_hooks.regression_gate._git_sha', return_value='deadbeef'):
            _write_baseline(f, 87.5, 42)
        data = json.loads(f.read_text())
        assert data['metrics']['coverage_pct'] == 87.5
        assert data['metrics']['tests_passed'] == 42
        assert data['git_sha'] == 'deadbeef'

    def test_none_values_default_to_zero(self, tmp_path: Path) -> None:
        f = tmp_path / '.quality-baseline.json'
        with patch('pre_commit_hooks.regression_gate._git_sha', return_value='abc'):
            _write_baseline(f, None, None)
        data = json.loads(f.read_text())
        assert data['metrics']['coverage_pct'] == 0.0
        assert data['metrics']['tests_passed'] == 0

    def test_file_ends_with_newline(self, tmp_path: Path) -> None:
        f = tmp_path / '.quality-baseline.json'
        with patch('pre_commit_hooks.regression_gate._git_sha', return_value='abc'):
            _write_baseline(f, 80.0, 5)
        assert f.read_text().endswith('\n')


# ─────────────────────────────────────────────────────────────────────────────
# _check
# ─────────────────────────────────────────────────────────────────────────────


class TestCheck:
    def _setup(
        self,
        tmp_path: Path,
        coverage_xml: str | None = COVERAGE_XML_85,
        junit_xml: str | None = JUNIT_XML_10_PASS,
        baseline: dict | None = None,  # type: ignore[type-arg]
    ) -> tuple[Path, Path, Path]:
        b = tmp_path / '.quality-baseline.json'
        c = tmp_path / 'coverage.xml'
        t = tmp_path / 'test-results.xml'
        if baseline is not None:
            b.write_text(json.dumps(baseline))
        if coverage_xml is not None:
            c.write_text(coverage_xml)
        if junit_xml is not None:
            t.write_text(junit_xml)
        return b, c, t

    def test_no_baseline_returns_0(self, tmp_path: Path) -> None:
        b, c, t = self._setup(tmp_path, baseline=None)
        assert _check(b, c, t) == 0

    def test_no_regression_returns_0(self, tmp_path: Path) -> None:
        b, c, t = self._setup(tmp_path, baseline=_baseline(tests=10, coverage=85.0))
        assert _check(b, c, t) == 0

    def test_coverage_regression_returns_1(self, tmp_path: Path) -> None:
        # Baseline 90%, current 85% → regression
        b, c, t = self._setup(
            tmp_path,
            coverage_xml=COVERAGE_XML_85,
            baseline=_baseline(tests=10, coverage=90.0),
        )
        assert _check(b, c, t) == 1

    def test_test_count_regression_returns_1(self, tmp_path: Path) -> None:
        # Baseline 10 tests, current 8 → regression
        b, c, t = self._setup(
            tmp_path,
            junit_xml=JUNIT_XML_8_PASS,
            baseline=_baseline(tests=10, coverage=85.0),
        )
        assert _check(b, c, t) == 1

    def test_both_regressions_returns_1(self, tmp_path: Path) -> None:
        b, c, t = self._setup(
            tmp_path,
            coverage_xml=COVERAGE_XML_85,
            junit_xml=JUNIT_XML_8_PASS,
            baseline=_baseline(tests=10, coverage=90.0),
        )
        assert _check(b, c, t) == 1

    def test_coverage_improved_returns_0(self, tmp_path: Path) -> None:
        # Baseline 80%, current 85% → no regression
        b, c, t = self._setup(tmp_path, baseline=_baseline(tests=10, coverage=80.0))
        assert _check(b, c, t) == 0

    def test_missing_coverage_report_warns_but_does_not_fail(self, tmp_path: Path) -> None:
        b, c, t = self._setup(tmp_path, coverage_xml=None, baseline=_baseline(10, 85.0))
        # Missing report should not block push — just warn
        assert _check(b, c, t) == 0

    def test_missing_test_report_warns_but_does_not_fail(self, tmp_path: Path) -> None:
        b, c, t = self._setup(tmp_path, junit_xml=None, baseline=_baseline(10, 85.0))
        assert _check(b, c, t) == 0


# ─────────────────────────────────────────────────────────────────────────────
# main()
# ─────────────────────────────────────────────────────────────────────────────


class TestMain:
    def test_write_baseline_mode(self, tmp_path: Path) -> None:
        cov = tmp_path / 'coverage.xml'
        cov.write_text(COVERAGE_XML_85)
        junit = tmp_path / 'results.xml'
        junit.write_text(JUNIT_XML_10_PASS)
        baseline = tmp_path / '.quality-baseline.json'

        with patch('pre_commit_hooks.regression_gate._git_sha', return_value='abc'):
            ret = main(
                [
                    '--write-baseline',
                    '--baseline',
                    str(baseline),
                    '--coverage-report',
                    str(cov),
                    '--test-report',
                    str(junit),
                ],
            )
        assert ret == 0
        data = json.loads(baseline.read_text())
        assert data['metrics']['coverage_pct'] == 85.0
        assert data['metrics']['tests_passed'] == 10

    def test_check_mode_no_regression(self, tmp_path: Path) -> None:
        cov = tmp_path / 'coverage.xml'
        cov.write_text(COVERAGE_XML_85)
        junit = tmp_path / 'results.xml'
        junit.write_text(JUNIT_XML_10_PASS)
        baseline = tmp_path / '.quality-baseline.json'
        baseline.write_text(json.dumps(_baseline(10, 80.0)))

        ret = main(
            [
                '--baseline',
                str(baseline),
                '--coverage-report',
                str(cov),
                '--test-report',
                str(junit),
            ],
        )
        assert ret == 0

    def test_check_mode_regression_detected(self, tmp_path: Path) -> None:
        cov = tmp_path / 'coverage.xml'
        cov.write_text(COVERAGE_XML_85)
        junit = tmp_path / 'results.xml'
        junit.write_text(JUNIT_XML_8_PASS)
        baseline = tmp_path / '.quality-baseline.json'
        baseline.write_text(json.dumps(_baseline(10, 90.0)))

        ret = main(
            [
                '--baseline',
                str(baseline),
                '--coverage-report',
                str(cov),
                '--test-report',
                str(junit),
            ],
        )
        assert ret == 1

    def test_no_baseline_skips_gracefully(self, tmp_path: Path) -> None:
        ret = main(
            [
                '--baseline',
                str(tmp_path / 'nope.json'),
                '--coverage-report',
                str(tmp_path / 'nope.xml'),
                '--test-report',
                str(tmp_path / 'nope2.xml'),
            ],
        )
        assert ret == 0
