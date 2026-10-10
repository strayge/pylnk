from io import BytesIO
from pathlib import Path
from struct import pack, unpack_from

import pytest

from pylnk3.structures.link_info import DRIVE_FIXED, LinkInfo


def _local_record(base_unicode: str = '', suffix_unicode: str = '') -> bytes:
    """Keep volume metadata explicit so defaults cannot mask layout failures."""
    info = LinkInfo()
    info.local = 1
    info.remote = 0
    info.drive_type = DRIVE_FIXED
    info.drive_serial = 0x12345678
    info.volume_label = 'VOL'
    info.local_base_path = r'C:\file.txt'
    info.local_base_path_unicode = base_unicode
    info.local_base_path_suffix_unicode = suffix_unicode
    stream = BytesIO()
    info.write(stream)
    return stream.getvalue()


def test_ascii_local_layout() -> None:
    """Header offsets must address actual ANSI records, not calculated model fields."""
    data = _local_record()
    label = b'VOL\x00'
    path = b'C:\\file.txt\x00'
    volume = pack('<4I', 16 + len(label), 3, 0x12345678, 16) + label
    size, header_size, flags, volume_offset, path_offset, network_offset, suffix_offset = unpack_from('<7I', data)

    assert header_size == 0x1C
    assert size == len(data) == 0x1C + len(volume) + len(path) + 1
    assert flags == 1
    assert volume_offset == 0x1C
    assert path_offset == volume_offset + len(volume)
    assert network_offset == 0
    assert suffix_offset == path_offset + len(path)
    assert data[volume_offset:path_offset] == volume
    assert data[path_offset:suffix_offset] == path
    assert data[suffix_offset:] == b'\x00'


@pytest.mark.parametrize(('base', 'suffix'), [
    (r'C:\folder', 'leaf.txt'),
    (r'C:\café', 'résumé'),
    (r'C:\📁', 'leaf.txt'),
    (r'C:\📁', ''),
    (r'C:\📁📂', 'leaf.txt'),
    (r'C:\📁', '😀'),
    (r'C:\📁', '😀🚀'),
])
def test_unicode_local_payload(base: str, suffix: str) -> None:
    """UTF16 payloads remain correct even when advertised lengths or offsets are wrong."""
    data = _local_record(base, suffix)
    path = b'C:\\file.txt\x00'
    base_bytes = base.encode('utf-16-le') + b'\x00\x00'
    suffix_bytes = suffix.encode('utf-16-le') + b'\x00\x00'
    _, header_size, flags, volume_offset, path_offset, network_offset, _, base_offset, _ = unpack_from('<9I', data)

    assert header_size == 0x24
    assert flags == 1
    assert volume_offset == header_size
    assert path_offset == header_size + 16 + len(b'VOL\x00')
    assert network_offset == 0
    assert base_offset == path_offset + len(path)
    assert data[path_offset:base_offset] == path
    assert data[base_offset:] == base_bytes + suffix_bytes + b'\x00'


@pytest.mark.parametrize('invariant', ['size', 'suffix_offset', 'suffix_payload'])
@pytest.mark.parametrize('base', [
    pytest.param(
        r'C:\folder', marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='ASCII base reserves two extra UTF16 bytes',
        ),
    ),
    pytest.param(
        r'C:\café', marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='BMP base reserves two extra UTF16 bytes',
        ),
    ),
    r'C:\📁',
    pytest.param(
        r'C:\📁📂', marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Two astral characters leave the base two bytes short',
        ),
    ),
])
def test_unicode_base_layout(base: str, invariant: str) -> None:
    """Isolate each header invariant so one known failure cannot hide another check."""
    data = _local_record(base, 'leaf.txt')
    base_bytes = base.encode('utf-16-le') + b'\x00\x00'
    suffix_bytes = b'l\x00e\x00a\x00f\x00.\x00t\x00x\x00t\x00\x00\x00'
    base_offset = 0x24 + 16 + len(b'VOL\x00') + len(b'C:\\file.txt\x00')
    expected_suffix_offset = base_offset + len(base_bytes)
    suffix_offset = unpack_from('<I', data, 0x20)[0]

    if invariant == 'size':
        assert unpack_from('<I', data)[0] == len(data)
    elif invariant == 'suffix_offset':
        assert suffix_offset == expected_suffix_offset
    else:
        assert data[suffix_offset:suffix_offset + len(suffix_bytes)] == suffix_bytes


@pytest.mark.parametrize('suffix', [
    '',
    'leaf.txt',
    'résumé',
    pytest.param(
        '😀', marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Suffix sizing counts characters instead of UTF16 code units',
        ),
    ),
    pytest.param(
        '😀🚀', marks=pytest.mark.xfail(
            strict=True, raises=AssertionError, reason='Suffix sizing omits both surrogate-pair code units',
        ),
    ),
])
def test_unicode_suffix_size(suffix: str) -> None:
    """A single astral base cancels its sizing defect, exposing suffix sizing independently."""
    data = _local_record(r'C:\📁', suffix)
    assert unpack_from('<I', data)[0] == len(data)


@pytest.mark.parametrize(('filename', 'ansi_path', 'unicode_path'), [
    ('local_file_unicode.lnk', b'C:\\dir\\subdir\\file\xe9\xf6.txt', None),
    ('local_file_2emoji.lnk', b'C:\\dir\\subdir\\file????.txt', r'C:\dir\subdir\file🎂💔.txt'),
    ('local_file_unicode2.lnk', b'C:\\dir\\subdir\\file??.txt', r'C:\dir\subdir\file漢字.txt'),
])
def test_native_local_link_info_layout(
    examples_path: str, filename: str, ansi_path: bytes, unicode_path: str | None,
) -> None:
    """Reference boundaries come from raw fields and encoded payloads, not the parser's model."""
    data = (Path(examples_path) / filename).read_bytes()
    assert unpack_from('<I', data)[0] == 0x4C
    assert unpack_from('<I', data, 0x14)[0] & 0x83 == 0x83
    id_list_size = unpack_from('<H', data, 0x4C)[0]
    start = 0x4E + id_list_size
    size = unpack_from('<I', data, start)[0]
    record = data[start:start + size]
    assert len(record) == size
    _, header_size, flags, volume_offset, path_offset, network_offset, suffix_offset = unpack_from('<7I', record)
    assert header_size == (0x24 if unicode_path is not None else 0x1C)
    assert flags == 1
    assert volume_offset == header_size
    assert network_offset == 0

    volume_size, drive_type, _, label_offset = unpack_from('<4I', record, volume_offset)
    assert drive_type == 3
    assert label_offset == 16
    assert volume_size >= 17
    assert volume_offset + volume_size <= path_offset < size
    assert record[volume_offset + label_offset:volume_offset + volume_size] == b'\x00'
    ansi_end = path_offset + len(ansi_path) + 1
    assert ansi_end <= size
    assert record[path_offset:ansi_end] == ansi_path + b'\x00'
    assert header_size <= suffix_offset < size
    assert record[suffix_offset:suffix_offset + 1] == b'\x00'

    if unicode_path is not None:
        base_offset, unicode_suffix_offset = unpack_from('<2I', record, 0x1C)
        expected_base = unicode_path.encode('utf-16-le') + b'\x00\x00'
        base_end = base_offset + len(expected_base)
        assert ansi_end <= base_offset < size
        assert base_end <= unicode_suffix_offset <= size - 2
        assert record[base_offset:base_end] == expected_base
        assert record[unicode_suffix_offset:unicode_suffix_offset + 2] == b'\x00\x00'
