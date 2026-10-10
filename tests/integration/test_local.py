import os

import pytest

from pylnk3 import Lnk
from pylnk3.structures.extra_data import ExtraData_PropertyStoreDataBlock, ExtraData_Unparsed
from pylnk3.structures.id_list.path import PathSegmentFileOrFolderEntry
from pylnk3.utils import read_write


@pytest.mark.parametrize(
    'filename,path',
    (
        ('mounted_folder1_file1.lnk', 'Z:\\Downloads\\folder1\\file1.txt'),
        ('mounted_folder1_file2.lnk', 'Z:\\Downloads\\folder1\\file12.txt'),
        ('mounted_folder2_file1.lnk', 'Z:\\Downloads\\folder12\\file1.txt'),
        ('mounted_folder2_file2.lnk', 'Z:\\Downloads\\folder12\\file12.txt'),
    ),
)
def test_local_mounted_share(examples_path: str, temp_filename: str, filename: str, path: str) -> None:
    """This links contains both local and network path."""
    full_filename = os.path.join(examples_path, filename)
    lnk = Lnk.from_file(full_filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_disk_link(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'local_disk.lnk')
    path = 'C:'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_file_link(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'local_file.lnk')
    path = 'C:\\Windows\\explorer.exe'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_folder_link(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'local_folder.lnk')
    path = 'C:\\Users\\stray\\Desktop\\New folder'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_send_to_fax(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'send_to_fax.lnk')
    path = '%windir%\\system32\\WFS.exe'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_recent1(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'recent1.lnk')
    path = '::{374DE290-123F-4565-9164-39C4925E467B}\\2020M09_01_contract.pdf'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_recent2(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'recent2.lnk')
    path = '::{088E3905-0323-4B02-9826-5D99428E115F}\\catastrophe_89f317b5c3.7z'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_empty_idlist(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'desktop.lnk')
    path = 'C:\\Users\\heznik\\Desktop'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_emoji(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'local_emoji.lnk')
    path = 'C:\\Users\\Public\\Downloads\\test❤️and🍰.txt'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path
    # check unicode fields in link_info
    assert lnk.link_info.local_base_path_unicode == path
    assert lnk.link_info.local_base_path_suffix_unicode == ''
    assert lnk2.link_info.local_base_path_unicode == path
    assert lnk2.link_info.local_base_path_suffix_unicode == ''


def test_local_thispc(examples_path: str, temp_filename: str) -> None:
    filename = os.path.join(examples_path, 'local_thispc.lnk')
    path = '%MY_COMPUTER%'
    lnk = Lnk.from_file(filename)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


def test_local_unknown_extra(examples_path: str, temp_filename: str) -> None:
    """Unknown extra-data blocks must retain their payload, not only their signature."""
    filename = os.path.join(examples_path, 'local_extra_0xa2000001.lnk')
    lnk = Lnk.from_file(filename)
    assert lnk.extra_data
    original_block = lnk.extra_data.blocks[0]
    assert isinstance(original_block, ExtraData_Unparsed)
    expected_payload = original_block.data
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.extra_data
    extra_block = lnk2.extra_data.blocks[0]
    assert isinstance(extra_block, ExtraData_Unparsed)
    assert extra_block._signature == 0xA2000001
    assert extra_block.data == expected_payload


@pytest.mark.parametrize(('filename', 'leaf', 'short_name', 'unicode_link_info'), [
    ('local_file_unicode.lnk', 'fileéö.txt', 'FILE~2.TXT', False),
    ('local_file_2emoji.lnk', 'file🎂💔.txt', 'FILE~1.TXT', True),
    ('local_file_unicode2.lnk', 'file漢字.txt', 'FILE~3.TXT', True),
])
def test_native_unicode_file_metadata(
    examples_path: str, filename: str, leaf: str, short_name: str, unicode_link_info: bool,
) -> None:
    """Known source values must be checked before a roundtrip can conceal parser losses."""
    lnk = Lnk.from_file(os.path.join(examples_path, filename))
    path = 'C:\\dir\\subdir\\' + leaf
    assert lnk.path == path
    assert lnk.relative_path == '.\\' + leaf
    assert lnk.work_dir == r'C:\dir\subdir'
    assert lnk.link_flags.IsUnicode
    assert lnk.link_info.local_base_path_unicode == (path if unicode_link_info else '')
    assert lnk.link_info.local_base_path_suffix_unicode == ''

    segments = [item for item in lnk.shell_item_id_list.items if isinstance(item, PathSegmentFileOrFolderEntry)]
    assert tuple(item.full_name for item in segments) == ('dir', 'subdir', leaf)
    assert tuple(item.short_name for item in segments) == ('dir', 'subdir', short_name)
    assert all(not item.flags.IsUnicode for item in segments)
    assert all(item.flags.IsDirectory and not item.flags.IsFile for item in segments[:-1])
    assert segments[-1].flags.IsFile and not segments[-1].flags.IsDirectory
    assert lnk.extra_data is not None
    assert len(lnk.extra_data.blocks) == 2
    tracker, properties = lnk.extra_data.blocks
    assert isinstance(tracker, ExtraData_Unparsed)
    assert tracker._signature == 0xA0000003
    assert isinstance(properties, ExtraData_PropertyStoreDataBlock)
    assert properties._signature == 0xA0000009


def test_native_cp1252_link_info_path(examples_path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """ANSI fields require the known source code page, which the shortcut does not identify."""
    monkeypatch.setattr(read_write, 'DEFAULT_CHARSET', 'cp1252')
    path = r'C:\dir\subdir\fileéö.txt'
    lnk = Lnk.from_file(os.path.join(examples_path, 'local_file_unicode.lnk'))
    assert lnk.link_info.local_base_path == path
    restored = Lnk.from_bytes(lnk.bytes())
    assert restored.path == path
    assert restored.link_info.local_base_path == path
