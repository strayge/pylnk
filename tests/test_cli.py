import os
import subprocess
import sys
from typing import Optional

from pylnk3 import Lnk


def quote_cmd(line: str) -> str:
    if sys.platform == 'win32':
        return f'"{line}"'
    return f"'{line}'"


def call_cli(params: str) -> Optional[str]:
    exec_path = 'pylnk3.py'
    result = subprocess.run(
        f'python {exec_path} {params}', check=True, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.decode()


def test_cli_create_local(temp_filename):
    path = 'C:\\folder\\file.txt'
    call_cli(f'c {quote_cmd(path)} {temp_filename}')
    lnk = Lnk(temp_filename)
    assert lnk.path == path


def test_cli_create_net(temp_filename):
    path = '\\\\192.168.1.1\\SHARE\\path\\file.txt'
    share = '\\\\192.168.1.1\\SHARE\\'
    call_cli(f'c {quote_cmd(path)} {temp_filename}')
    lnk = Lnk(temp_filename)
    assert lnk.path == share


def test_cli_parse(examples_path):
    path = os.path.join(examples_path, 'local_file.lnk')
    output = call_cli(f'p {path}')
    assert 'Path: C:\\Windows\\explorer.exe' in output
