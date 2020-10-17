import os

import pytest

from pylnk3 import ExtraData_EnvironmentVariableDataBlock, Lnk


def check_path(lnk: Lnk, path: str):
    assert lnk.path == path


def check_extra_env_path(lnk: Lnk, path: str):
    extra_env = [
        block for block in lnk.extra_data.blocks
        if isinstance(block, ExtraData_EnvironmentVariableDataBlock)
    ][0]
    # target_unicode fulfilled with \x00 and share name stored in upper case
    assert extra_env.target_unicode.rstrip('\x00').lower() == path.lower()


@pytest.mark.parametrize(
    'filename,path',
    (
        ('net_folder1_file1.lnk', '\\\\192.168.138.2\\STORAGE\\Downloads\\folder1\\file1.txt'),
        ('net_folder1_file2.lnk', '\\\\192.168.138.2\\STORAGE\\Downloads\\folder1\\file12.txt'),
        ('net_folder2_file1.lnk', '\\\\192.168.138.2\\STORAGE\\Downloads\\folder12\\file1.txt'),
        ('net_folder2_file2.lnk', '\\\\192.168.138.2\\STORAGE\\Downloads\\folder12\\file12.txt'),
    ),
)
def test_network_lnk(examples_path, temp_filename, filename: str, path: str):
    full_filename = os.path.join(examples_path, filename)
    # read
    lnk = Lnk(full_filename)
    check_path(lnk, path)
    check_extra_env_path(lnk, path)
    # write
    lnk.save(temp_filename)
    # check
    lnk2 = Lnk(temp_filename)
    # check_path(lnk2, path)  # FIXME: something wrong with lnk.link_info.base_name
    check_extra_env_path(lnk2, path)
