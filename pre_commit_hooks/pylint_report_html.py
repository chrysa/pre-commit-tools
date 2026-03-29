#!/usr/bin/python3
"""Hook to run Pylint and produce an HTML report from the JSON output."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from pylint.lint import Run
from pylint_report.pylint_report import main as report_main

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(_handler)


class PylintHtmlReport(PreCommitTools):
    """Run Pylint over the given files and convert the JSON output to an HTML report."""

    output_html: Path
    output_json: Path
    namespace_args: argparse.Namespace
    pylint_args: list[str]

    def clean_json_report(self) -> None:
        """Remove the intermediate JSON report if --output-json was not explicitly set."""
        if self.namespace_args.output_json is None:
            logger.debug('clean json report')
            self.output_json.unlink(missing_ok=True)

    def convert_json_to_html(self) -> None:
        """Convert the JSON Pylint report to an HTML file."""
        logger.debug('convert json to html')
        report_main(argv=[self.output_json.as_posix(), '-o', self.output_html.as_posix()])

    def _resolve_path(self, value: str | Path) -> Path:
        """Resolve a string or Path to an absolute Path and ensure its parent directory exists."""
        p = Path(value) if isinstance(value, str) else value
        out = p if p.is_absolute() else Path.cwd() / p
        out.parent.mkdir(parents=True, exist_ok=True)
        return out

    def generate_output_paths(self) -> None:
        """Resolve and store the HTML and JSON output paths."""
        self.output_html = self._resolve_path(self.namespace_args.output_html)
        json_arg = self.namespace_args.output_json
        self.output_json = self._resolve_path(json_arg if json_arg is not None else 'pylint_report.json')

    def get_args(self, *, argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
        """Parse CLI arguments and store them on the instance."""
        logger.debug('parse arguments')
        self.namespace_args, self.pylint_args = super().get_args(argv=argv)
        return self.namespace_args, self.pylint_args

    def run_pylint(self) -> None:
        """Run Pylint with the configured arguments."""
        logger.debug('run pylint')
        Run(self.pylint_args)

    def set_params(self, *, help_msg: str = '', arguments: list[tuple[str, dict[str, object]]] | None = None) -> None:
        """Configure the argument parser with Pylint report specific arguments."""
        logger.debug('define parser')
        super().set_params(help_msg='run pylint and generate an HTML report')
        self.parser.add_argument(
            '--output-html',
            action='store',
            help='directory to write the HTML report to (default: ./html)',
            default='html',
        )
        self.parser.add_argument(
            '--output-json',
            action='store',
            help='path for the intermediate JSON report; deleted after conversion unless specified',
            default=None,
        )

    def update_pylint_args(self) -> None:
        """Append Pylint output format and path arguments before running."""
        logger.debug('update pylint args')
        self.pylint_args.extend(['--exit-zero', '--persistent=n', '--reports=n', '--score=n'])
        self.pylint_args.extend(
            [f'--output={self.output_json.as_posix()}', '--output-format=pylint_report.CustomJsonReporter'],
        )
        self.pylint_args.extend(self.namespace_args.filenames)


def main(argv: Sequence[str] | None = None) -> int:
    """Run Pylint and generate an HTML report; return 1 if the report is non-empty."""
    instance = PylintHtmlReport()
    instance.set_params()
    instance.get_args(argv=argv)
    instance.generate_output_paths()
    instance.update_pylint_args()
    instance.run_pylint()
    instance.convert_json_to_html()
    instance.clean_json_report()
    return int(instance.file_exist(file=instance.output_html) and not instance.file_empty(file=instance.output_html))


if __name__ == '__main__':
    raise SystemExit(main())
