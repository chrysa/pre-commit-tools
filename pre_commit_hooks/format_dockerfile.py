#!/usr/bin/python3
from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NewType

from dockerfile_parse import DockerfileParser

from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

KEYWORDS_GROUP = ['ADD', 'ARG', 'COPY']

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

Line = NewType('Line', dict[str, int | str])


# TODO: separate block for litteral ARGS and ARGS composed with variable same for env
@dataclass
class FormatDockerfile:
    dockerfile: Path = None
    content: str = ''
    parser: DockerfileParser = DockerfileParser()
    return_value: int = 0

    @staticmethod
    def _get_instruction(*, line: Line):
        logger.debug(f'get instuction type for {line}')
        return line['instruction']

    @staticmethod
    def _remove_split_lines(*, content):
        logger.info('remove split lines ..........')
        return re.sub(r' \\\n +', ' ', content)

    def _get_line_content(self, *, line):
        logger.debug(f'get line content {line} ..........')
        return line['content']

    def _is_grouped_keyword(self, *, line: Line) -> bool:
        logger.debug(f"test {line['instruction']} is a grouped keyword ..........")
        return self._get_instruction(line=line) in KEYWORDS_GROUP

    def _is_same_as_previous(self, *, index: int) -> bool:
        logger.debug(
            f"test if line {index} type {self.parser.structure[index-1]['instruction']} is same as previous {self.parser.structure[index]['instruction']} ..........",
        )
        if index == 0:
            state = False
        else:
            state = self._get_instruction(line=self.parser.structure[index - 1]) == self._get_instruction(
                line=self.parser.structure[index],
            )
        return state

    def _is_type(self, *, line: Line, instruction_type: str) -> bool:
        logger.debug(f'check if line {line} is {instruction_type} ..........')
        return self._get_instruction(line=line) == instruction_type

    def format_file(self, *, file):
        logger.info(f'format file {file}')
        self.parser.content = self._remove_split_lines(content=self.parser.content)
        for index, line in enumerate(self.parser.structure):
            line_content = self._get_line_content(line=line)
            if self._is_type(line=line, instruction_type='COMMENT'):
                logger.info('format CONTENT ..........')
                if index > 0:
                    self.content += '\n'
                self.content += line_content
            elif (
                self._is_type(line=line, instruction_type='EXPOSE')
                or self._is_type(line=line, instruction_type='FROM')
                or self._is_type(line=line, instruction_type='USER')
                or self._is_type(line=line, instruction_type='WORKDIR')
            ):
                logger.info(f'format {self._get_instruction(line=line)} ..........')
                self.content += '\n\n' + line_content
            elif self._is_type(line=line, instruction_type='ENV'):
                logger.info('format ENV ..........')
                multiline = ' \\\n  '.join(line_content.split(' ')[1:])
                self.content += '\n' + f'ENV {multiline}'
            elif self._is_type(line=line, instruction_type='RUN'):
                logger.info('format RUN ..........')
                multiline = ' \\\n  && '.join(list(map(str.strip, line_content.split('&&'))))
                self.content += '\n' + multiline
            elif self._is_type(line=line, instruction_type='HEALTHCHECK'):
                logger.info('format HEALTHCHECK ..........')
                multiline = '\\\n   CMD '.join(line_content.split('CMD'))
                self.content += '\n' + multiline
                self.content += '\n\n' + line_content
            elif self._is_grouped_keyword(line=line):
                logger.info('format grouped line ..........')
                if self._is_same_as_previous(index=index):
                    logger.debug('same line ..........')
                    self.content += line_content
                else:
                    logger.debug('not same line ..........')
                    self.content += '\n' + line_content
            else:
                logger.info('format simple line ..........')
                self.content += '\n' + line_content

    def load_dockerfile(self, *, dockerfile_path: Path) -> None:
        logger.info(f'read {dockerfile_path} ..........')
        self.parser.dockerfile_path = dockerfile_path
        with open(dockerfile_path) as stream:
            self.parser.content = stream.read()

    def save(self, *, file: Path) -> None:
        if self.content == self.parser.content:
            status = 'unchanged'
        else:
            logger.debug(f'update {self.dockerfile} ..........')
            with open(file, 'w+') as stream:
                stream.seek(0)
                stream.write(self.content)
                stream.truncate()
            status = 'formatted'
            self.return_value = 1
        print(f'{file} .......... {status}')


def main(argv: Sequence[str] | None = None) -> int:
    format_dockerfile_class = FormatDockerfile()
    tools_instance = PreCommitTools()
    args = tools_instance.set_params(help_msg='format dockerfile', argv=argv)
    for file in args.filenames:
        file = Path(file)
        format_dockerfile_class.content = ''
        format_dockerfile_class.load_dockerfile(dockerfile_path=file)
        format_dockerfile_class.format_file(file=Path().absolute() / file)
        format_dockerfile_class.save(file=file)
    return format_dockerfile_class.return_value


if __name__ == '__main__':
    raise SystemExit(main())
