"""Tests for the coverage parser of scripts/quality_gate.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'quality_gate.py'


def _parser() -> Any:
    spec = importlib.util.spec_from_file_location('quality_gate', _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.QualityGate.__new__(module.QualityGate)


PYTEST_PROGRESS_TRAP = (
    'tests/test_compose_dev_hot_reload.py::TestX::test_service_named_dev_is_covered PASSED [ 13%]\n'
    'TOTAL                       3265    200   1212    149    92%\n'
    'Required test coverage of 85% reached. Total coverage: 91.71%\n'
)


class TestParseCoverage:
    def test_ignores_pytest_progress_on_a_covered_named_test(self) -> None:
        """A test named '..._is_covered' prints [ 13%]; that is not the coverage."""
        assert _parser()._parse_coverage(PYTEST_PROGRESS_TRAP) == 91.71

    def test_reads_the_pytest_cov_summary(self) -> None:
        out = 'Required test coverage of 85% reached. Total coverage: 87.50%\n'
        assert _parser()._parse_coverage(out) == 87.5

    def test_reads_the_total_row(self) -> None:
        out = 'Name    Stmts   Miss  Cover\nTOTAL     100     10    90%\n'
        assert _parser()._parse_coverage(out) == 90.0

    def test_reads_a_plain_total_coverage_line(self) -> None:
        assert _parser()._parse_coverage('Total coverage: 64.2%\n') == 64.2

    def test_returns_minus_one_when_absent(self) -> None:
        assert _parser()._parse_coverage('no numbers here\n') == -1.0

    def test_progress_output_alone_is_not_coverage(self) -> None:
        out = 'tests/test_x.py::test_everything_is_covered PASSED [ 42%]\n'
        assert _parser()._parse_coverage(out) == -1.0
