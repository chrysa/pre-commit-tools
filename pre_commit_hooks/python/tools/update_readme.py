import subprocess  # nosec
from pathlib import Path


def create_content(*, command: str, content: str) -> str:
    content_content = '\n```bash\n'
    content_content += f'$ {command}\n\n'
    content_content += f'{content}'
    content_content += '```\n'
    return content_content


def run_command(*, command: str) -> str:
    with subprocess.Popen(command, stdout=subprocess.PIPE, shell=True) as cmd_process_stream:  # nosec
        output, _ = cmd_process_stream.communicate()
        cmd_process_stream.wait()
        return bytes.decode(output, 'utf-8')


def update_readme(
    *, start_tag: str, end_tag: str, command: str, command_content_processed: str = None, readme_file_path: Path = None
) -> None:
    if readme_file_path is None:
        readme_file_path = Path(__file__).resolve().parent.parent / 'README.md'
    with open(readme_file_path, 'r+') as f:
        content = f.read()
        pos_start = content.find(start_tag)
        pos_end = content.find(end_tag)
        if pos_start != -1 and pos_end != -1 and pos_end > pos_start:
            update_content: str
            if command_content_processed is not None:
                update_content = command_content_processed
            else:
                update_content = run_command(command=command)
            content = content[: pos_start + len(start_tag)]
            content += update_content
            content = content[pos_end:]
        f.seek(0)
        f.write(content)
        f.truncate()
