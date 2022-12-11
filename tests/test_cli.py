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


def test_cli_create_local(temp_filename: str) -> None:
    path = 'C:\\folder\\file.txt'
    call_cli(f'c {quote_cmd(path)} {temp_filename}')
    lnk = Lnk(temp_filename)
    assert lnk.path == path


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
