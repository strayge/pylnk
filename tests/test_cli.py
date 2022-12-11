import os
import subprocess
import sys
from typing import Optional

import pytest

from pylnk3 import Lnk
from pylnk3.structures import PathSegmentEntry
from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.structures.id_list.path import TYPE_FILE, TYPE_FOLDER


def quote_cmd(line: str) -> str:
    if sys.platform == 'win32':
        return f'"{line}"'
    return f"'{line}'"  # type: ignore[unreachable]


def call_cli(params: str) -> Optional[str]:
    # copy full environ, otherwise required SYSTEMROOT will be missing on Windows
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath('.')
    exec_path = 'pylnk3'
    result = subprocess.run(
        f'{sys.executable} {exec_path} {params}', check=True, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env,
    )
    return result.stdout.decode()


def check_segment_type(segment: IDListEntry, expected_type: str) -> None:
    assert isinstance(segment, PathSegmentEntry)
    assert segment.type == expected_type


def test_cli_create_local_file(temp_filename: str) -> None:
    path = 'C:\\folder\\file.txt'
    call_cli(f'c {quote_cmd(path)} {temp_filename}')
    lnk = Lnk(temp_filename)
    assert lnk.path == path


@pytest.mark.parametrize(
    ('path', 'params', 'last_entry_type'),
    (
        # detect by dot in name
        ('C:\\folder\\file.txt', '', TYPE_FILE),
        ('C:\\folder\\folder', '', TYPE_FOLDER),
        # overrive with cli argument
        ('C:\\folder\\folder.with.txt', '--directory', TYPE_FOLDER),
        ('C:\\folder\\file_without_txt', '--file', TYPE_FILE),
    ),
)
def test_cli_local_link_type(temp_filename: str, path: str, params: str, last_entry_type: str) -> None:
    call_cli(f'c {quote_cmd(path)} {temp_filename} {params}')
    lnk = Lnk(temp_filename)
    check_segment_type(lnk.shell_item_id_list.items[-2], TYPE_FOLDER)
    check_segment_type(lnk.shell_item_id_list.items[-1], last_entry_type)


def test_cli_create_net(temp_filename: str) -> None:
    path = '\\\\192.168.1.1\\SHARE\\path\\file.txt'
    share = '\\\\192.168.1.1\\SHARE\\'
    call_cli(f'c {quote_cmd(path)} {temp_filename}')
    lnk = Lnk(temp_filename)
    assert lnk.path == share


def test_cli_parse(examples_path: str) -> None:
    path = os.path.join(examples_path, 'local_file.lnk')
    output = call_cli(f'p {path}')
    assert output
    assert 'Path: C:\\Windows\\explorer.exe' in output
