import os

import pytest

from pylnk3 import Lnk


@pytest.mark.parametrize(
    'filename,path',
    (
        ('mounted_folder1_file1.lnk', '%MY_COMPUTER%\\Z:\\Downloads\\folder1\\file1.txt'),
        ('mounted_folder1_file2.lnk', '%MY_COMPUTER%\\Z:\\Downloads\\folder1\\file12.txt'),
        ('mounted_folder2_file1.lnk', '%MY_COMPUTER%\\Z:\\Downloads\\folder12\\file1.txt'),
        ('mounted_folder2_file2.lnk', '%MY_COMPUTER%\\Z:\\Downloads\\folder12\\file12.txt'),
    ),
)
def test_local_mounted_share(examples_path, temp_filename, filename: str, path: str):
    """This links contains both local and network path."""
    full_filename = os.path.join(examples_path, filename)
    lnk = Lnk(full_filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk(temp_filename)
    assert lnk2.path == path


def test_local_disk_link(examples_path, temp_filename):
    filename = os.path.join(examples_path, 'local_disk.lnk')
    path = '%MY_COMPUTER%\\C:'
    lnk = Lnk(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk(temp_filename)
    assert lnk2.path == path


def test_local_file_link(examples_path, temp_filename):
    filename = os.path.join(examples_path, 'local_file.lnk')
    path = '%MY_COMPUTER%\\C:\\Windows\\explorer.exe'
    lnk = Lnk(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk(temp_filename)
    assert lnk2.path == path
