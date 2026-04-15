#!/usr/bin/python3
"""Hook to format Dockerfiles: add shebang, merge consecutive identical instructions."""

from __future__ import annotations

import logging
import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NewType

from dockerfile_parse import DockerfileParser

Line = NewType('Line', dict[str, int | str])

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

SHEBANG = '# syntax=docker/dockerfile:1.4'

# Matches ARG lines that reference another variable: ARG FOO=${BAR} or ARG FOO=${BAR}-extra
_ARG_VAR_PATTERN = re.compile(r'ARG\s+\w+\s*=\s*.*\$\{')


def _load_config(config_path: Path) -> dict[str, bool]:
    """Load formatter config from a TOML file. Returns empty dict if not found."""
    if not config_path.exists():
        return {}
    try:
        data = tomllib.loads(config_path.read_text(encoding='utf-8'))
        return data.get('format-dockerfiles', {})
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _sort_arg_env_blocks(content: str, *, sort_args: bool, sort_envs: bool, separate_arg_blocks: bool) -> str:
    """Post-process Dockerfile content to sort consecutive ARG/ENV blocks."""
    lines = content.split('\n')
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        instruction = stripped.split()[0].upper() if stripped.split() else ''

        if instruction == 'ARG' and (sort_args or separate_arg_blocks):
            # Collect consecutive ARG lines
            block: list[str] = []
            while i < len(lines) and lines[i].strip().upper().startswith('ARG'):
                block.append(lines[i])
                i += 1
            if separate_arg_blocks:
                literal = [ln for ln in block if not _ARG_VAR_PATTERN.search(ln)]
                variable = [ln for ln in block if _ARG_VAR_PATTERN.search(ln)]
                if sort_args:
                    literal.sort(key=str.casefold)
                    variable.sort(key=str.casefold)
                if literal and variable:
                    result.extend(literal)
                    result.append('')
                    result.extend(variable)
                else:
                    result.extend(literal + variable)
            elif sort_args:
                block.sort(key=str.casefold)
                result.extend(block)
            else:
                result.extend(block)
        elif instruction == 'ENV' and sort_envs:
            block = []
            while i < len(lines) and lines[i].strip().upper().startswith('ENV'):
                block.append(lines[i])
                i += 1
            block.sort(key=str.casefold)
            result.extend(block)
        else:
            result.append(line)
            i += 1
    return '\n'.join(result)


@dataclass
class FormatDockerfile:
    """Dataclass that parses and reformats a Dockerfile in-place."""

    dockerfile: Path | None = None
    content: str = ''
    _raw_content: str = field(default='', repr=False)
    origin_content: list[Line] = field(default_factory=list)
    parser: DockerfileParser = field(default_factory=DockerfileParser)
    return_value: int = 0
    sort_args: bool = False
    sort_envs: bool = False
    separate_arg_blocks: bool = False

    @staticmethod
    def _get_line_instruction(*, line: Line) -> str:
        logger.debug(f'get instuction type for {line}')
        return str(line['instruction'])

    @staticmethod
    def _get_line_content(*, line: Line) -> str:
        logger.debug(f'get line content {line} ..........')
        return str(line['content']).strip()

    @staticmethod
    def _remove_split_lines(*, content: str) -> str:
        logger.debug('remove split lines ..........')
        return re.sub(r' \\\n +', ' ', content)

    def _as_header(self) -> bool:
        logger.debug('verify if header is present ..........')
        line = self.parser.structure[0]
        return self._is_type(line=line, instruction_type='COMMENT') and self._get_line_content(line=line) == SHEBANG

    def _define_header(self) -> None:
        logger.debug('add shebang ..........')
        self.content += SHEBANG

    def _format_healthcheck_line(self, *, line_content: str) -> None:
        logger.debug('format HEALTHCHECK ..........')
        multiline = ' \\\n    CMD '.join(list(map(str.strip, line_content.split('CMD'))))
        self.content += '\n' + multiline

    def _file_as_changed(self) -> bool:
        return (self.content.strip() + '\n') != self._raw_content

    def _format_env_line(self, *, line_content: str) -> None:
        logger.debug('format ENV ..........')
        multiline = ' \\\n    '.join(line_content.split(' ')[1:])
        self.content += '\n' + f'ENV {multiline}'

    def _format_run_line(self, *, index: int, line_content: str) -> None:
        logger.debug('format RUN ..........')
        line_content = line_content.replace('RUN ', '')
        data = self._split_run_content(line_content)
        if self._is_same_as_previous(index=index):
            self.content += data
        else:
            self.content += '\n'
            if data.startswith(' \\\n    && '):
                data = data.replace(' \\\n    && ', '', 1)
            self.content += '\n' + 'RUN ' + data

    def _split_run_content(self, line_content: str) -> str:
        if line_content.startswith('--'):
            split_list = list(map(str.strip, line_content.split('&&')))
            return ' \\\n    && '.join(split_list)
        elif '&&' in line_content:
            return ' \\\n    && '.join(list(map(str.strip, line_content.split('&&'))))
        else:
            return ' \\\n    && ' + line_content

    def _format_simple_line(self, *, line_content: str, line_instruction: str) -> None:
        logger.debug(f'format {line_instruction} ..........')
        self.content += line_content

    def _is_type(self, *, line: Line, instruction_type: str) -> bool:
        logger.debug(f'check if line {line} is {instruction_type} ..........')
        return self._get_line_instruction(line=line) == instruction_type

    def _validate_header(self) -> list[Line]:
        logger.debug('validate shebang ..........')
        if self._as_header():
            logger.debug('shebang is present ..........')
            self._format_simple_line(
                line_content=self._get_line_content(line=self.parser.structure[0]),
                line_instruction='COMMENT',
            )
            return self.parser.structure[1:]
        else:
            self._define_header()
            return self.parser.structure

    def _get_previous_instruction(self, *, index: int) -> str:
        return self._get_line_instruction(line=self.origin_content[index - 1])

    def _is_same_as_previous(self, *, index: int) -> bool:
        return self._get_line_instruction(line=self.origin_content[index]) == self._get_previous_instruction(
            index=index,
        )

    def _format_line(self, *, index: int, line: Line) -> None:
        line_content = self._get_line_content(line=line)
        line_instruction = self._get_line_instruction(line=self.origin_content[index])
        if line_instruction in [
            'ADD',
            'ARG',
            'CMD',
            'COMMENT',
            'COPY',
            'ENTRYPOINT',
            'EXPOSE',
            'SHELL',
            'USER',
            'WORKDIR',
        ]:
            self._add_newline_if_needed(index=index)
            self._format_simple_line(line_content=line_content, line_instruction=line_instruction)
        elif self._is_type(line=line, instruction_type='ENV'):
            self.content += '\n'
            self._format_env_line(line_content=line_content)
        elif self._is_type(line=line, instruction_type='FROM'):
            self.content += '\n\n'
            self._format_simple_line(line_content=line_content, line_instruction=line_instruction)
        elif self._is_type(line=line, instruction_type='HEALTHCHECK'):
            self.content += '\n'
            self._format_healthcheck_line(line_content=line_content)
        elif self._is_type(line=line, instruction_type='RUN'):
            self._format_run_line(index=index, line_content=line_content)
        else:
            self.content += '\n' + line_content

    def _add_newline_if_needed(self, *, index: int) -> None:
        if self._is_same_as_previous(index=index):
            self.content += '\n'
        else:
            self.content += '\n\n'

    def format_file(self) -> None:
        logger.debug('format file')
        self.parser.content = self._remove_split_lines(content=self.parser.content)
        self.origin_content = self._validate_header()
        for index, line in enumerate(self.origin_content):
            self._format_line(index=index, line=line)
        if self.sort_args or self.sort_envs or self.separate_arg_blocks:
            self.content = _sort_arg_env_blocks(
                self.content,
                sort_args=self.sort_args,
                sort_envs=self.sort_envs,
                separate_arg_blocks=self.separate_arg_blocks,
            )

    def load_dockerfile(self, *, dockerfile_path: Path) -> None:
        logger.debug(f'read {dockerfile_path} ..........')
        self.parser.dockerfile_path = dockerfile_path
        with open(dockerfile_path) as stream:
            raw_text = stream.read()
        self._raw_content = raw_text  # Save original BEFORE DockerfileParser writes
        self.parser.content = raw_text

    def save(self, *, file: Path) -> None:
        if self._file_as_changed():
            logger.debug(f'update {file} ..........')
            with open(file, 'w') as stream:
                stream.write(self.content.strip() + '\n')
            print(f'{file} .......... formatted')
            self.return_value = 1
        else:
            # Restore original: format_file() writes intermediate content to disk as a side effect
            with open(file, 'w') as stream:
                stream.write(self._raw_content)
            print(f'{file} .......... unchanged')


def main(argv: Sequence[str] | None = None) -> int:
    """Format each Dockerfile in args and return 1 if any file was modified."""
    import argparse

    parser = argparse.ArgumentParser(description='format dockerfile')
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('-c', '--config', default=None, help='Path to .format-dockerfiles.toml config file')
    parser.add_argument('--sort-args', action='store_true', default=False, help='Sort ARG instructions alphabetically')
    parser.add_argument('--sort-envs', action='store_true', default=False, help='Sort ENV instructions alphabetically')
    parser.add_argument(
        '--separate-arg-blocks',
        action='store_true',
        default=False,
        help='Separate literal ARGs from variable-dependent ARGs',
    )
    args = parser.parse_args(argv)

    # Load config file (--config overrides default search)
    cfg: dict[str, bool] = {}
    config_path = Path(args.config) if args.config else Path('.format-dockerfiles.toml')
    cfg = _load_config(config_path)

    sort_args: bool = args.sort_args or bool(cfg.get('sort_args', False))
    sort_envs: bool = args.sort_envs or bool(cfg.get('sort_envs', False))
    separate_arg_blocks: bool = args.separate_arg_blocks or bool(cfg.get('separate_arg_blocks', False))

    any_formatted = False
    for file in args.filenames:
        filepath = Path(file)
        format_dockerfile_class = FormatDockerfile(
            sort_args=sort_args,
            sort_envs=sort_envs,
            separate_arg_blocks=separate_arg_blocks,
        )
        format_dockerfile_class.load_dockerfile(dockerfile_path=filepath)
        format_dockerfile_class.format_file()
        format_dockerfile_class.save(file=filepath)
        if format_dockerfile_class.return_value == 1:
            any_formatted = True
    return 1 if any_formatted else 0


if __name__ == '__main__':
    raise SystemExit(main())
