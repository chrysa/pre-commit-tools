#!/usr/bin/python3
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import NewType
from typing import TYPE_CHECKING

from dockerfile_parse import DockerfileParser

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

if TYPE_CHECKING:
    from collections.abc import Sequence

    Line = NewType('Line', dict[str, int | str])

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

SHEBANG = '# syntax=docker/dockerfile:1.4'


# TODO: separate block for litteral ARGS and ARGS composed with variable
# TODO: order alphabeticly ARGS
# TODO: order alphabeticly ENV
# TODO: add config file support
@dataclass
class FormatDockerfile:
    dockerfile: Path = None
    content: str = ''
    origin_content: list[dict] = field(default_factory=list)
    parser: DockerfileParser = DockerfileParser()
    return_value: int = 0

    @staticmethod
    def _get_line_instruction(*, line: Line) -> str:
        logger.debug(f'get instuction type for {line}')
        return line['instruction']

    @staticmethod
    def _get_line_content(*, line: Line) -> str:
        logger.debug(f'get line content {line} ..........')
        return line['content'].strip()

    @staticmethod
    def _remove_split_lines(*, content) -> str:
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
        return repr(self.content) != repr(self.parser.content)

    def _format_env_line(self, *, line_content: str) -> None:
        logger.debug('format ENV ..........')
        multiline = ' \\\n    '.join(line_content.split(' ')[1:])
        self.content += '\n' + f'ENV {multiline}'

    def _format_run_line(self, *, index: int, line_content: str) -> None:
        logger.debug('format RUN ..........')
        line_content = line_content.replace('RUN ', '')
        if '&&' in line_content:
            data = ' \\\n    && '.join(list(map(str.strip, line_content.split('&&'))))
        else:
            data = ' \\\n    && ' + line_content
        if self._is_same_as_previous(index=index):
            self.content += data
        else:
            self.content += "\n"
            if data.startswith(' \\\n    && '):
                data = data.replace(' \\\n    && ', '', 1)
            self.content += '\n' + 'RUN ' + data

    def _format_simple_line(self, *, line_content: str, line_instruction: str) -> None:
        logger.debug(f'format {line_instruction} ..........')
        self.content += line_content

    def _is_type(self, *, line: Line, instruction_type: str) -> bool:
        logger.debug(f'check if line {line} is {instruction_type} ..........')
        return self._get_line_instruction(line=line) == instruction_type

    def _validate_header(self):
        logger.debug('validate shebang ..........')
        if self._as_header():
            logger.debug('shebang is present ..........')
            self._format_simple_line(
                line_content=self._get_line_content(line=self.parser.structure[0]),
                line_instruction="COMMENT",
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
            'HEALTHCHECK',
            'SHELL',
            'USER',
            'WORKDIR',
        ]:
            if self._is_same_as_previous(index=index):
                self.content += "\n"
            else:
                self.content += "\n\n"
            self._format_simple_line(line_content=line_content, line_instruction=line_instruction)
        elif self._is_type(line=line, instruction_type='ENV'):
            self.content += "\n"
            self._format_env_line(line_content=line_content)
        elif self._is_type(line=line, instruction_type='FROM'):
            self.content += "\n\n"
            self._format_healthcheck_line(line_content=line_content)
        elif self._is_type(line=line, instruction_type='RUN'):
            self._format_run_line(index=index, line_content=line_content)
        else:
            self.content += '\n' + line_content

    def format_file(self) -> None:
        logger.debug('format file')
        self.parser.content = self._remove_split_lines(content=self.parser.content)
        self.origin_content = self._validate_header()
        for index, line in enumerate(self.origin_content):
            self._format_line(index=index, line=line)

    def load_dockerfile(self, *, dockerfile_path: Path) -> None:
        logger.debug(f'read {dockerfile_path} ..........')
        self.parser.dockerfile_path = dockerfile_path
        with open(dockerfile_path) as stream:
            self.parser.content = stream.read()

    def save(self, *, file: Path) -> None:
        if self._file_as_changed():
            logger.debug(f'update {file} ..........')
            with open(file, 'w+') as stream:
                stream.seek(0)
                stream.write(self.content)
                stream.truncate()
            print(f'{file} .......... formatted')
            self.return_value = 1
        else:
            print(f'{file} .......... unchabged')


def main(argv: Sequence[str] | None = None) -> int:
    format_dockerfile_class = FormatDockerfile()
    tools_instance = PreCommitTools()
    args = tools_instance.set_params(help_msg='format dockerfile', argv=argv)
    for file in args.filenames:
        file = Path(file)
        format_dockerfile_class.content = ''
        format_dockerfile_class.load_dockerfile(dockerfile_path=file)
        format_dockerfile_class.format_file()
        format_dockerfile_class.save(file=file)
    return format_dockerfile_class.return_value


if __name__ == '__main__':
    raise SystemExit(main())
