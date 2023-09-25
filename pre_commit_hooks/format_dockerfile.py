#!/usr/bin/python3
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dockerfile_parse import DockerfileParser
from pre_commit_hooks.tools.pre_commit_tools import PreCommitTools

KEYWORDS_GROUP = ['ADD', 'ARG', 'COPY']


# TODO: separate block for litteral ARGS and ARGS composed with variable
@dataclass
class FormatDockerfile:
    dockerfile: Path = None
    content: str = ''
    parser: DockerfileParser = DockerfileParser()
    return_value: int = 0

    @staticmethod
    def _get_instruction(*, line: dict[str, str | int]):
        # print(f"get instuction type for {line}")
        return line['instruction']

    @staticmethod
    def _get_line_content(*, line):
        return line['content']

    @staticmethod
    def _remove_split_lines(*, content):
        # print("remove split lines ..........")
        return re.sub(r' \\\n +', ' ', content)

    def _is_grouped_keyword(self, *, line: dict[str, int | str]) -> bool:
        # print(f"test {line['instruction']} is a grouped keyword ..........")
        return self._get_instruction(line=line) in KEYWORDS_GROUP

    def _is_same_as_previous(self, *, index: int) -> bool:
        # print(f"test if line {index} type {self.parser.structure[index-1]['instruction']} is same as previous {self.parser.structure[index]['instruction']} ..........")
        if index == 0:
            state = False
        else:
            state = self._get_instruction(line=self.parser.structure[index - 1]) == self._get_instruction(
                line=self.parser.structure[index],
            )
        return state

    def _is_type(self, *, line: dict[str, int | str], instruction_type: str) -> bool:
        # print(f"check if line {line} is {instruction_type} ..........")
        return self._get_instruction(line=line) == instruction_type

    def load_dockerfile(self, *, dockerfile_path: Path) -> None:
        # print(f'read {dockerfile_path} ..........')
        with open(dockerfile_path) as stream:
            self.parser.content = self._remove_split_lines(content=stream.read())

    def format_file(self, *, file):
        # format
        for index, line in enumerate(self.parser.structure):
            if self._is_type(line=line, instruction_type='COMMENT'):
                self.content += self._get_line_content(line=line)
            elif self._is_type(line=line, instruction_type='FROM'):
                self.content += '\n'
                self.content += '\n'
                self.content += self._get_line_content(line=line)
            elif self._is_type(line=line, instruction_type='ENV'):
                # print("format multi line env ..........")
                multiline = ' \\\n  '.join(self._get_line_content(line=line).split(' ')[1:])
                self.content += '\n'
                self.content += f'ENV {multiline}'
            elif self._is_type(line=line, instruction_type='RUN'):
                multiline = ' \\\n  && '.join(self._get_line_content(line=line).split('&&'))
                self.content += '\n'
                self.content += multiline
            elif self._is_type(line=line, instruction_type='HEALTHCHECK'):
                # print("format healthcheck ..........")
                multiline = '\\\n   CMD '.join(self._get_line_content(line=line).split('CMD'))
                self.content += '\n'
                self.content += multiline
            elif self._is_grouped_keyword(line=line):
                if self._is_same_as_previous(index=index):
                    self.content += self._get_line_content(line=line)
                else:
                    self.content += '\n'
                    self.content += self._get_line_content(line=line)
            else:
                self.content += '\n'
                self.content += self._get_line_content(line=line)

    def save(self, *, file: Path) -> None:
        if self.content != self.parser.content:
            # print(f"update {self.dockerfile} ..........")
            with open(file, 'w+') as stream:
                stream.seek(0)
                stream.write(self.content)
                stream.truncate()
            status = 'formatted'
            self.return_value = 1
        else:
            status = 'unchanged'
        print(f'save {file} .......... {status}')


def main(argv: Sequence[str] | None = None) -> int:
    format_dockerfile_class = FormatDockerfile()
    tools_instance = PreCommitTools()
    args = tools_instance.set_params(help_msg='format dockerfile', argv=argv)
    for file in args.filenames:
        file = Path(file)
        format_dockerfile_class.load_dockerfile(dockerfile_path=file)
        format_dockerfile_class.format_file(file=Path().absolute() / file)
        format_dockerfile_class.save(file=file)
    return format_dockerfile_class.return_value


if __name__ == '__main__':
    raise SystemExit(main())
