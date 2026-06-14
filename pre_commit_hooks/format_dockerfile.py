#!/usr/bin/python3
"""Hook to format Dockerfiles: add shebang, merge consecutive identical instructions."""

from __future__ import annotations

import json
import logging
import re
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
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

# Default header injected when a Dockerfile has none. Adding it modifies the
# file, so the hook returns 1 and the commit is blocked until it is committed.
SHEBANG = '# syntax=docker/dockerfile:1.4'
_RUN_JOIN = ' \\\n    && '

# Matches any pinned syntax-frontend header, e.g.
#   # syntax=docker/dockerfile:1
#   # syntax=docker/dockerfile:1.7
#   # syntax=docker/dockerfile:1.7.0
_SYNTAX_HEADER_PATTERN = re.compile(
    r'^#\s*syntax\s*=\s*docker/dockerfile:(\d+(?:\.\d+){0,2})\s*$',
)

# How many newer stable releases the pinned version may trail before we warn.
_VERSION_LAG_THRESHOLD = 3

# Docker Hub tag listing for the official syntax frontend image.
_DOCKERHUB_TAGS_URL = 'https://hub.docker.com/v2/repositories/docker/dockerfile/tags?page_size=100'
_DOCKERHUB_TIMEOUT = 3.0
# Only plain X.Y.Z stable tags — excludes 'latest', 'labs', '*-rc*', etc.
_STABLE_TAG_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')

# Cache the tag listing so we hit the network at most once per day instead of
# on every commit. Network failures fall back to "no warning", never an error.
_TAGS_CACHE_FILE = Path(tempfile.gettempdir()) / 'format_dockerfile_syntax_tags.json'
_TAGS_CACHE_TTL = 86400  # seconds (24h)


def _version_tuple(version: str) -> tuple[int, int, int]:
    """Normalise a dotted version to a 3-tuple so X.Y and X.Y.Z compare fairly."""
    parts = [int(part) for part in version.split('.')]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


def _read_tags_cache() -> list[str] | None:
    """Return cached stable tags if the cache is fresh, else None."""
    try:
        raw = json.loads(_TAGS_CACHE_FILE.read_text(encoding='utf-8'))
        if time.time() - float(raw['fetched_at']) < _TAGS_CACHE_TTL:
            tags = raw['tags']
            return [str(tag) for tag in tags]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return None


def _write_tags_cache(tags: list[str]) -> None:
    """Persist stable tags with a fetch timestamp; ignore write failures."""
    try:
        _TAGS_CACHE_FILE.write_text(
            json.dumps({'fetched_at': time.time(), 'tags': tags}),
            encoding='utf-8',
        )
    except OSError:
        pass


def _fetch_dockerfile_tags() -> list[str]:
    """Return stable docker/dockerfile tags from Docker Hub (cached, best-effort).

    Returns an empty list on any network/parse error so version-lag checking is
    skipped silently — it must never break an offline commit.
    """
    if (cached := _read_tags_cache()) is not None:
        return cached
    try:
        request = urllib.request.Request(  # noqa: S310 — fixed HTTPS Docker Hub URL
            _DOCKERHUB_TAGS_URL,
            headers={'User-Agent': 'format-dockerfile-hook'},
        )
        with urllib.request.urlopen(  # noqa: S310 — fixed HTTPS Docker Hub URL
            request,
            timeout=_DOCKERHUB_TIMEOUT,
        ) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return []
    tags = [
        result['name']
        for result in payload.get('results', [])
        if isinstance(result.get('name'), str) and _STABLE_TAG_PATTERN.match(result['name'])
    ]
    _write_tags_cache(tags)
    return tags


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


def _sort_arg_env_blocks(
    content: str,
    *,
    sort_args: bool,
    sort_envs: bool,
    separate_arg_blocks: bool,
) -> str:
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

    def _header_version(self) -> str | None:
        """Return the pinned syntax version if line 0 is a syntax header, else None.

        Accepts any version (1, 1.7, 1.7.0…), not only the default SHEBANG, so an
        up-to-date header is preserved instead of being duplicated or downgraded.
        """
        logger.debug('verify if syntax header is present ..........')
        if not self.parser.structure:
            return None
        line = self.parser.structure[0]
        if not self._is_type(line=line, instruction_type='COMMENT'):
            return None
        match = _SYNTAX_HEADER_PATTERN.match(self._get_line_content(line=line))
        return match.group(1) if match else None

    def _check_version_lag(self, *, version: str) -> None:
        """Warn (non-blocking) if the pinned version trails latest by >= threshold."""
        tags = _fetch_dockerfile_tags()
        if not tags:
            return
        pinned = _version_tuple(version)
        newer = [tag for tag in tags if _version_tuple(tag) > pinned]
        if len(newer) >= _VERSION_LAG_THRESHOLD:
            latest = max(tags, key=_version_tuple)
            target = self.dockerfile if self.dockerfile is not None else 'Dockerfile'
            logger.warning(
                f'{target}: syntax version {version} is {len(newer)} releases behind '
                f'latest {latest}; consider updating the # syntax header',
            )

    def _define_header(self) -> None:
        logger.debug('add shebang ..........')
        self.content += SHEBANG

    def _format_healthcheck_line(self, *, line_content: str) -> None:
        logger.debug('format HEALTHCHECK ..........')
        multiline = ' \\\n    CMD '.join(
            list(map(str.strip, line_content.split('CMD'))),
        )
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
            if data.startswith(_RUN_JOIN):
                data = data.replace(_RUN_JOIN, '', 1)
            self.content += '\n' + 'RUN ' + data

    def _split_run_content(self, line_content: str) -> str:
        if line_content.startswith('--'):
            split_list = list(map(str.strip, line_content.split('&&')))
            return _RUN_JOIN.join(split_list)
        elif '&&' in line_content:
            return _RUN_JOIN.join(list(map(str.strip, line_content.split('&&'))))
        else:
            return _RUN_JOIN + line_content

    def _format_simple_line(self, *, line_content: str, line_instruction: str) -> None:
        logger.debug(f'format {line_instruction} ..........')
        self.content += line_content

    def _is_type(self, *, line: Line, instruction_type: str) -> bool:
        logger.debug(f'check if line {line} is {instruction_type} ..........')
        return self._get_line_instruction(line=line) == instruction_type

    def _validate_header(self) -> list[Line]:
        logger.debug('validate syntax header ..........')
        if (version := self._header_version()) is not None:
            logger.debug(f'syntax header present (version {version}) ..........')
            self._format_simple_line(
                line_content=self._get_line_content(line=self.parser.structure[0]),
                line_instruction='COMMENT',
            )
            self._check_version_lag(version=version)
            return self.parser.structure[1:]
        self._define_header()
        return self.parser.structure

    def _get_previous_instruction(self, *, index: int) -> str:
        return self._get_line_instruction(line=self.origin_content[index - 1])

    def _is_same_as_previous(self, *, index: int) -> bool:
        return self._get_line_instruction(
            line=self.origin_content[index],
        ) == self._get_previous_instruction(
            index=index,
        )

    _SIMPLE_INSTRUCTIONS = frozenset(
        {
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
        },
    )

    def _format_line(self, *, index: int, line: Line) -> None:
        line_content = self._get_line_content(line=line)
        line_instruction = self._get_line_instruction(line=self.origin_content[index])
        if line_instruction in self._SIMPLE_INSTRUCTIONS:
            self._add_newline_if_needed(index=index)
            self._format_simple_line(
                line_content=line_content,
                line_instruction=line_instruction,
            )
        elif self._is_type(line=line, instruction_type='ENV'):
            self.content += '\n'
            self._format_env_line(line_content=line_content)
        elif self._is_type(line=line, instruction_type='FROM'):
            self.content += '\n\n'
            self._format_simple_line(
                line_content=line_content,
                line_instruction=line_instruction,
            )
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
        self.dockerfile = dockerfile_path
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
            print(f'{file} .......... formatted')  # print-detection: disable -- CLI output
            self.return_value = 1
        else:
            # Restore original: format_file() writes intermediate content to disk as a side effect
            with open(file, 'w') as stream:
                stream.write(self._raw_content)
            print(f'{file} .......... unchanged')  # print-detection: disable -- CLI output


def main(argv: Sequence[str] | None = None) -> int:
    """Format each Dockerfile in args and return 1 if any file was modified."""
    import argparse

    parser = argparse.ArgumentParser(description='format dockerfile')
    parser.add_argument('filenames', nargs='*')
    parser.add_argument(
        '-c',
        '--config',
        default=None,
        help='Path to .format-dockerfiles.toml config file',
    )
    parser.add_argument(
        '--sort-args',
        action='store_true',
        default=False,
        help='Sort ARG instructions alphabetically',
    )
    parser.add_argument(
        '--sort-envs',
        action='store_true',
        default=False,
        help='Sort ENV instructions alphabetically',
    )
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
    separate_arg_blocks: bool = args.separate_arg_blocks or bool(
        cfg.get('separate_arg_blocks', False),
    )

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
