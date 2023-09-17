#!/usr/bin/python3
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dockerfile_parse import DockerfileParser
from pre_commit_hooks.python.tools.pre_commit_tools import PreCommitTools

KEYWORDS_GROUP = ['ADD', 'ARG', 'COPY']
KEYWORDS_SEPARATE = [
    'ENTRYPOINT',
    'HEALTHCHECK',
    'ENV',
    'FROM',
    'RUN',
    'SHELL',
    'USER',
]


@dataclass
class FormatDockerfile:
    dockerfile: Path = None
    content: str = None
    parser: DockerfileParser = DockerfileParser()

    def _get_lines_startswith(self, *, keyword):
        lines = []
        for line in self.content.splitlines():
            if line.startswith(keyword):
                lines.append(line)
        return lines

    def format(self):
        self.parser.content = self.content
        self.content = self.parser.content

    def format_grouped_keyword(self, *, keyword):
        # print(f"fomat keyword {keyword} ..........")
        line_tab = self.content.split('\n')
        for index, line in enumerate(line_tab):
            if line.startswith(keyword):
                if not line_tab[index - 1].startswith(keyword) and not line_tab[index - 1].startswith(
                    f'--replace--{keyword}',
                ):
                    line_tab[index] = f'--replace--{line}'
                elif not line_tab[index + 1].startswith(keyword):
                    line_tab[index] = f'{line}--replace--'
        self.content = '\n'.join(line_tab)

    def remove_multiple_space(self):
        # print("remove multiple space ..........")
        self.content = re.sub(r' +', ' ', self.content)

    def format_multilines_env(self):
        # print("format multi line env ..........")
        for line in self._get_lines_startswith(keyword='ENV'):
            multiline = ' \\\n  '.join(line.split(' ')[1:])
            self.content = self.content.replace(line, f'ENV {multiline}')

    def format_multilines_run(self):
        # print("format multi line cmd ..........")
        for line in self._get_lines_startswith(keyword='RUN'):
            multiline = ' \\\n  && '.join(line.split('&&'))
            self.content = self.content.replace(line, multiline)

    def format_split_healthcheck(self):
        for line in self._get_lines_startswith(keyword='HEALTHCHECK'):
            multiline = '\\\n   CMD '.join(line.split('CMD'))
            self.content = self.content.replace(line, multiline)

    def read(self, *, dockerfile: Path):
        # print(f"read {dockerfile} ..........")
        self.dockerfile = dockerfile
        with open(self.dockerfile) as stream:
            self.content = stream.read()

    def remove_multiple_empty_lines(self):
        self.content = re.sub(r'\n+', '\n', self.content)

    def remove_split_lines(self):
        # print(f"remove split lines ..........")
        self.content = re.sub(r' \\\n +', ' ', self.content)

    def save(self):
        # print(f"update {self.dockerfile} ..........")
        with open(self.dockerfile, 'w+') as stream:
            stream.seek(0)
            stream.write(self.content)
            stream.truncate()

    def format_separated_keyword(self, *, keyword):
        # print(f"fomat keyword {keyword} ..........")
        line_tab = self.content.split('\n')
        for index, line in enumerate(line_tab):
            if line.startswith(keyword):
                line_tab[index] = f'\n{line}\n'
        self.content = '\n'.join(line_tab)

    def format_file(self, *, file):
        self.read(dockerfile=file)
        self.format()
        self.remove_multiple_empty_lines()
        self.remove_split_lines()
        self.remove_multiple_space()
        for keyword in KEYWORDS_GROUP:
            self.format_grouped_keyword(keyword=keyword)
        self.content = self.content.replace('--replace--', '\n')
        for keyword in KEYWORDS_SEPARATE:
            self.format_separated_keyword(keyword=keyword)
        self.format_multilines_run()
        self.format_multilines_env()
        self.format_split_healthcheck()
        self.save()


def main(argv: Sequence[str] | None = None) -> int:
    format_dockerfile_class = FormatDockerfile()
    tools_instance = PreCommitTools()
    args = tools_instance.set_params(help_msg='format dockerfile', argv=argv)
    for file in args.filenames:
        format_dockerfile_class.format_file(file=Path().absolute() / file)
        print(f'save {file} .......... done')


if __name__ == '__main__':
    raise SystemExit(main())
