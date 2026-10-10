from datetime import datetime
from pathlib import Path
from struct import pack, unpack_from

import pytest

from pylnk3.structures.id_list.path import PathSegmentFileOrFolderEntry


def _segment_bytes(short_name: str, full_name: str, is_file: bool = False) -> bytes:
    """Fixed metadata prevents filesystem state and wall-clock time from influencing bytes."""
    entry = PathSegmentFileOrFolderEntry()
    entry.short_name = short_name
    entry.full_name = full_name
    entry.flags.IsFile = is_file
    entry.flags.IsDirectory = not is_file
    entry.file_size = 123 if is_file else 0
    entry.modified = datetime(2024, 1, 2, 3, 4, 0)
    entry.created = datetime(2024, 1, 2, 3, 4, 0)
    entry.accessed = datetime(2024, 1, 2, 3, 4, 0)
    return entry.bytes


@pytest.mark.parametrize(('short_name', 'full_name', 'is_file', 'short_bytes', 'unicode_flag'), [
    ('folder', 'folder', False, b'folder\x00\x00', 0),
    ('a.txt', 'a.txt', True, b'a.txt\x00', 0),
    ('PROGRA~1', 'Program Files', False, b'PROGRA~1\x00\x00', 0),
    ('目录', '目录', False, b'\xee\x76\x55\x5f\x00\x00', 4),
    ('📁', '📁', False, b'\x3d\xd8\xc1\xdc\x00\x00', 4),
    ('😀🚀', '😀🚀.txt', True, b'\x3d\xd8\x00\xde\x3d\xd8\x80\xde\x00\x00', 4),
])
def test_segment_payload(
    short_name: str, full_name: str, is_file: bool, short_bytes: bytes, unicode_flag: int,
) -> None:
    """Short-name padding and flags must locate a real version-three Unicode extension."""
    data = _segment_bytes(short_name, full_name, is_file)
    dos_date = ((2024 - 1980) << 9) | (1 << 5) | 2
    dos_time = (3 << 11) | (4 << 5)
    flags = 2 if is_file else 1
    expected_header = pack('<HIHH', 0x30 | flags | unicode_flag, 123 if is_file else 0, dos_date, dos_time)
    extension_start = 12 + len(short_bytes)
    long_bytes = full_name.encode('utf-16-le') + b'\x00\x00'

    assert data[:10] == expected_header
    assert data[12:extension_start] == short_bytes
    assert data[extension_start + 2:extension_start + 20] == pack(
        '<HI6H', 3, 0xBEEF0004, dos_date, dos_time, dos_date, dos_time, 20, 0,
    )
    assert data[extension_start + 20:-2] == long_bytes
    assert len(data) - extension_start == 20 + len(long_bytes) + 2


@pytest.mark.parametrize('is_file', [
    False,
    pytest.param(
        True, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError,
            reason='File shell items incorrectly set the directory file attribute.',
        ),
    ),
], ids=['directory', 'file'])
def test_segment_directory_attribute(is_file: bool) -> None:
    """The directory attribute must agree with the file-or-folder classification."""
    data = _segment_bytes('entry', 'entry', is_file)
    attributes = unpack_from('<H', data, 10)[0]
    assert bool(attributes & 0x10) is not is_file


@pytest.mark.parametrize(('short_name', 'full_name', 'short_byte_count'), [
    pytest.param(
        'folder', 'folder', 8, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='ASCII extension declares 38 bytes but emits 36',
        ),
    ),
    pytest.param(
        'PROGRA~1', 'Program Files', 10, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Distinct ASCII names declare 52 extension bytes but emit 50',
        ),
    ),
    pytest.param(
        '目录', '目录', 6, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='BMP long name reserves two extra extension bytes',
        ),
    ),
    ('📁', '📁', 6),
    pytest.param(
        '😀🚀', '😀🚀.txt', 10, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Two astral characters make the extension two bytes too short',
        ),
    ),
])
def test_extension_size(short_name: str, full_name: str, short_byte_count: int) -> None:
    """The extension size includes its own field, Unicode terminator and trailing offset."""
    data = _segment_bytes(short_name, full_name)
    extension_start = 12 + short_byte_count
    assert unpack_from('<H', data, extension_start)[0] == len(data) - extension_start


@pytest.mark.parametrize(('short_name', 'short_byte_count'), [
    ('folder', 8),
    ('a.txt', 6),
    ('目录', 6),
    pytest.param(
        '📁', 6, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Short-name offset omits one surrogate-pair code unit',
        ),
    ),
    pytest.param(
        '😀🚀', 10, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Short-name offset omits two surrogate-pair code units',
        ),
    ),
])
def test_extension_trailing_offset(short_name: str, short_byte_count: int) -> None:
    """The trailing offset addresses the extension relative to the enclosing ItemID size field."""
    data = _segment_bytes(short_name, '📁')
    extension_start = 12 + short_byte_count
    assert unpack_from('<H', data, len(data) - 2)[0] == extension_start + 2


@pytest.mark.parametrize(('filename', 'short_name', 'full_name'), [
    ('local_file_unicode.lnk', 'FILE~2.TXT', 'fileéö.txt'),
    ('local_file_2emoji.lnk', 'FILE~1.TXT', 'file🎂💔.txt'),
    ('local_file_unicode2.lnk', 'FILE~3.TXT', 'file漢字.txt'),
])
def test_native_file_extension_layout(examples_path: str, filename: str, short_name: str, full_name: str) -> None:
    """A reference extension must bound real UTF16 payloads, including surrogate pairs."""
    data = (Path(examples_path) / filename).read_bytes()
    id_list_size = unpack_from('<H', data, 0x4C)[0]
    id_list = data[0x4E:0x4E + id_list_size]
    assert len(id_list) == id_list_size
    cursor = 0
    item = b''
    while True:
        assert cursor + 2 <= len(id_list)
        item_size = unpack_from('<H', id_list, cursor)[0]
        if item_size == 0:
            assert cursor + 2 == len(id_list)
            break
        assert item_size >= 2 and cursor + item_size <= len(id_list)
        item = id_list[cursor + 2:cursor + item_size]
        cursor += item_size

    assert unpack_from('<H', item)[0] == 0x32
    assert not unpack_from('<H', item, 10)[0] & 0x10
    short_bytes = short_name.encode('ascii') + b'\x00'
    short_bytes += b'\x00' * (len(short_bytes) % 2)
    extension_start = 12 + len(short_bytes)
    assert item[12:extension_start] == short_bytes
    extension_size, version, signature = unpack_from('<HHI', item, extension_start)
    assert version == 9
    assert signature == 0xBEEF0004
    assert extension_start + extension_size == len(item)
    long_offset = unpack_from('<H', item, extension_start + 16)[0]
    assert long_offset == 0x2E
    long_start = extension_start + long_offset
    assert item[long_start:-2] == full_name.encode('utf-16-le') + b'\x00\x00'
    assert unpack_from('<H', item, len(item) - 2)[0] == extension_start + 2
