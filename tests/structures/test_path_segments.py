from datetime import datetime
from pathlib import Path
from struct import pack, pack_into, unpack_from

import pytest

from pylnk3.exceptions import FormatException
from pylnk3.structures.id_list.path import PathSegmentFileOrFolderEntry


@pytest.mark.parametrize(('flags', 'label'), [
    (0x01, 'FOLDER'),
    (0x02, 'FILE'),
    (0x05, 'FOLDER'),
    (0x06, 'FILE'),
    (0x00, 'FILE_OR_FOLDER'),
    (0x03, 'FILE_OR_FOLDER'),
])
def test_segment_text_classification(flags: int, label: str) -> None:
    """Diagnostics must use classification flags without guessing from names or changing metadata."""
    entry = PathSegmentFileOrFolderEntry()
    entry.full_name = 'entry.txt'
    entry.flags.set_flags(flags)
    assert str(entry) == f'<PathSegmentFileOrFolderEntry: entry.txt ({label})>'
    assert entry.type == 'FILE_OR_FOLDER'
    assert entry.flags.bytes == flags


def _segment_bytes(
    short_name: str, full_name: str, is_file: bool = False, localized_name: str | None = None,
) -> bytes:
    """Fixed metadata prevents filesystem state and wall-clock time from influencing bytes."""
    entry = PathSegmentFileOrFolderEntry()
    entry.short_name = short_name
    entry.full_name = full_name
    entry.localized_name = localized_name
    entry.flags.IsFile = is_file
    entry.flags.IsDirectory = not is_file
    entry.file_size = 123 if is_file else 0
    entry.modified = datetime(2024, 1, 2, 3, 4, 0)
    entry.created = datetime(2024, 1, 2, 3, 4, 0)
    entry.accessed = datetime(2024, 1, 2, 3, 4, 0)
    return entry.bytes


def test_extension_name_offsets() -> None:
    """Valid extension names take precedence over primary names, including gaps between fields."""
    extension = (
        pack('<HHI6H', 44, 3, 0xBEEF0004, 0, 0, 0, 0, 24, 36)
        + b'\xaa' * 4 + b'L\x00o\x00n\x00g\x00\x00\x00'
        + b'\xbb' * 2 + b'label\x00' + pack('<H', 20)
    )
    raw = pack('<HIHHH', 0x32, 7, 0, 0, 0x20) + b'SHORT\x00' + extension
    entry = PathSegmentFileOrFolderEntry(raw)
    assert entry.path == entry.full_name == 'Long'
    assert entry.short_name == 'SHORT'
    assert entry.localized_name == 'label'
    restored = PathSegmentFileOrFolderEntry(entry.bytes)
    assert restored.path == 'Long'
    assert restored.localized_name == 'label'


@pytest.mark.parametrize('damage', ['size', 'name-offset', 'localized-offset', 'terminator'])
def test_unusable_extension_preserves_item(damage: str) -> None:
    """Unusable optional metadata must not hide the primary name or be discarded on save."""
    raw = bytearray(_segment_bytes('SHORT', 'Long'))
    extension_start = 18
    if damage == 'size':
        pack_into('<H', raw, extension_start, len(raw))
    elif damage == 'name-offset':
        pack_into('<H', raw, extension_start + 16, 2)
    elif damage == 'localized-offset':
        pack_into('<H', raw, extension_start + 18, 20)
    else:
        raw[-4:-2] = b'X\x00'
        raw.extend(b'\x00\x00')  # Outside the declared extension, not its missing terminator.
    entry = PathSegmentFileOrFolderEntry(bytes(raw))
    assert entry.path == entry.short_name == 'SHORT'
    assert entry.full_name is None
    assert entry.created is None and entry.accessed is None
    assert entry.localized_name is None
    assert entry.bytes == raw


def test_following_opaque_extension_is_preserved() -> None:
    """A recognized first extension must not cause additional unknown blocks to disappear."""
    raw = _segment_bytes('SHORT', 'Long') + pack('<HHI', 8, 0, 0xBEEF9999)
    entry = PathSegmentFileOrFolderEntry(raw)
    assert entry.path == 'Long'
    assert entry.bytes == raw


@pytest.mark.parametrize('change_flags', [False, True], ids=['name', 'flags'])
def test_opaque_item_edits_are_not_silently_lost(examples_path: str, change_flags: bool) -> None:
    """Opaque passthrough must reject edits rather than ignore them or discard retained bytes."""
    raw = (Path(examples_path) / 'local_invalid_beef0004.lnk').read_bytes()[0x7D:0xCB]
    entry = PathSegmentFileOrFolderEntry(raw)
    if change_flags:
        entry.flags.IsDirectory = False
    else:
        entry.full_name = 'Changed'
    with pytest.raises(FormatException, match='opaque'):
        _ = entry.bytes


def test_truncated_primary_name_is_not_recovered() -> None:
    """The fallback applies to optional extensions, not an unreadable mandatory name."""
    raw = pack('<HIHHH', 0x31, 0, 0, 0, 0x10) + b'unterminated'
    with pytest.raises(EOFError):
        PathSegmentFileOrFolderEntry(raw)


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


@pytest.mark.parametrize('is_file', [False, True], ids=['directory', 'file'])
def test_segment_directory_attribute(is_file: bool) -> None:
    """The directory attribute must agree with the file-or-folder classification."""
    data = _segment_bytes('entry', 'entry', is_file)
    attributes = unpack_from('<H', data, 10)[0]
    assert bool(attributes & 0x10) is not is_file


@pytest.mark.parametrize(('short_name', 'full_name', 'short_byte_count'), [
    ('folder', 'folder', 8),
    ('PROGRA~1', 'Program Files', 10),
    ('目录', '目录', 6),
    ('📁', '📁', 6),
    ('😀🚀', '😀🚀.txt', 10),
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
    ('📁', 6),
    ('😀🚀', 10),
])
def test_extension_trailing_offset(short_name: str, short_byte_count: int) -> None:
    """The trailing offset addresses the extension relative to the enclosing ItemID size field."""
    data = _segment_bytes(short_name, '📁')
    extension_start = 12 + short_byte_count
    assert unpack_from('<H', data, len(data) - 2)[0] == extension_start + 2


@pytest.mark.parametrize(('localized_name', 'localized_bytes', 'version', 'full_offset', 'localized_offset'), [
    (None, b'', 3, 20, 0),
    ('', b'\x00\x00', 9, 46, 60),
    ('目录', b'\xee\x76\x55\x5f\x00\x00', 9, 46, 60),
    ('😀🚀', b'\x3d\xd8\x00\xde\x3d\xd8\x80\xde\x00\x00', 9, 46, 60),
])
def test_localized_extension_layout(
    localized_name: str | None, localized_bytes: bytes, version: int, full_offset: int, localized_offset: int,
) -> None:
    """Independent offsets and payloads distinguish absent names from present empty UTF16 names."""
    data = _segment_bytes('SHORT', 'Full📁', localized_name=localized_name)
    extension_start = 18  # Fixed header and the terminated, even-length ASCII short name.
    full_bytes = b'F\x00u\x00l\x00l\x00\x3d\xd8\xc1\xdc\x00\x00'
    expected_size = full_offset + len(full_bytes) + len(localized_bytes) + 2

    assert data[12:extension_start] == b'SHORT\x00'
    assert unpack_from('<HHI', data, extension_start) == (expected_size, version, 0xBEEF0004)
    assert unpack_from('<H', data, extension_start + 16)[0] == full_offset
    if version == 9:
        assert data[extension_start + 18:extension_start + 36] == b'\x00' * 18
        assert unpack_from('<H', data, extension_start + 36)[0] == localized_offset
        assert data[extension_start + 38:extension_start + 46] == b'\x00' * 8
        assert data[extension_start + localized_offset:-2] == localized_bytes
    else:
        assert unpack_from('<H', data, extension_start + 18)[0] == 0
    full_start = extension_start + full_offset
    assert data[full_start:full_start + len(full_bytes)] == full_bytes
    assert len(data) == extension_start + expected_size
    assert unpack_from('<H', data, len(data) - 2)[0] == extension_start + 2

    restored = PathSegmentFileOrFolderEntry(data)
    assert restored.full_name == 'Full📁'
    assert restored.localized_name == localized_name


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
