import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pylnk3 import Lnk
from pylnk3.structures import PathSegmentFileOrFolderEntry
from pylnk3.structures.id_list.base import IDListEntry


def call_cli(*params: str) -> str:
    """Keep argument boundaries identical on Windows and POSIX shells."""
    project_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(
        [sys.executable, '-m', 'pylnk3', *params], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=project_root, env=env, text=True, encoding='utf-8',
    )
    return result.stdout


def check_segment_type(segment: IDListEntry, is_file: bool) -> None:
    assert isinstance(segment, PathSegmentFileOrFolderEntry)
    assert segment.flags.IsFile is is_file
    assert segment.flags.IsDirectory is not is_file


def test_cli_create_local_file(temp_filename: str) -> None:
    path = 'C:\\folder with spaces\\file.txt'
    call_cli('c', path, temp_filename)
    lnk = Lnk.from_file(temp_filename)
    assert lnk.path == path


def test_cli_create_local_file_unicode(temp_filename: str) -> None:
    path = 'C:\\тест\\ööö\\👀file👀.txt'
    call_cli('c', path, temp_filename)
    lnk = Lnk.from_file(temp_filename)
    assert lnk.path == path


@pytest.mark.parametrize(
    ('path', 'params', 'last_entry_file'),
    (
        ('C:\\folder\\file.txt', (), True),
        ('C:\\folder\\folder', (), False),
        ('C:\\folder\\folder.with.txt', ('--directory',), False),
        ('C:\\folder\\file_without_txt', ('--file',), True),
    ),
)
def test_cli_local_link_type(
    temp_filename: str, path: str, params: tuple[str, ...], last_entry_file: bool,
) -> None:
    call_cli('c', path, temp_filename, *params)
    lnk = Lnk.from_file(temp_filename)
    check_segment_type(lnk.shell_item_id_list.items[-2], False)
    check_segment_type(lnk.shell_item_id_list.items[-1], last_entry_file)


def test_cli_create_net(temp_filename: str) -> None:
    """A generated network shortcut must retain the path inside its share."""
    path = '\\\\192.168.1.1\\SHARE\\path\\file.txt'
    call_cli('c', path, temp_filename)
    assert Lnk.from_file(temp_filename).path == path


def test_cli_parse(examples_path: str) -> None:
    path = os.path.join(examples_path, 'local_file.lnk')
    output = call_cli('p', path)
    assert 'Path: C:\\Windows\\explorer.exe' in output


@pytest.mark.parametrize(
    'is_unicode',
    (True, False),
    ids=('unicode', 'ansi'),
)
def test_cli_json_stringdata(temp_filename: str, is_unicode: bool) -> None:
    """JSON output must be usable for either valid StringData representation."""
    lnk = Lnk()
    lnk.link_flags.IsUnicode = is_unicode
    lnk.description = 'hello'
    lnk.save(temp_filename)
    output = call_cli('parse', temp_filename, '--json')
    result = json.loads(output)
    assert result['description'] == 'hello'
