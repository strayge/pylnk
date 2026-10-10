from io import BytesIO
from struct import pack, unpack_from

import pytest

from pylnk3.utils.read_write import read_sized_string, write_sized_string


@pytest.mark.parametrize(('text', 'unicode'), [
    ('', True),
    ('plain', True),
    ('café', True),
    ('A😀', True),
    ('😀🚀', True),
    ('plain', False),
])
def test_stringdata_write(text: str, unicode: bool) -> None:
    """CharacterCount must count UTF16 code units or ANSI bytes, without adding a terminator."""
    stream = BytesIO()
    write_sized_string(text, stream, string=unicode)
    data = stream.getvalue()
    payload = text.encode('utf-16-le' if unicode else 'ascii')
    expected_count = len(payload) // 2 if unicode else len(payload)

    assert unpack_from('<H', data)[0] == expected_count
    assert len(data) == 2 + len(payload)
    assert data[2:] == payload


@pytest.mark.parametrize(('payload', 'unicode', 'expected'), [
    (b'', True, ''),
    (b'p\x00l\x00a\x00i\x00n\x00', True, 'plain'),
    (b'c\x00a\x00f\x00\xe9\x00', True, 'café'),
    (b'A\x00\x3d\xd8\x00\xde', True, 'A😀'),
    (b'\x3d\xd8\x00\xde\x3d\xd8\x80\xde', True, '😀🚀'),
    (b'plain', False, b'plain'),
])
def test_stringdata_read(payload: bytes, unicode: bool, expected: str | bytes) -> None:
    """Manually encoded records must consume only their payload and retain ANSI byte semantics."""
    count = len(payload) // 2 if unicode else len(payload)
    sentinel = b'\x7f\x00\x00'
    stream = BytesIO(pack('<H', count) + payload + sentinel)

    assert read_sized_string(stream, string=unicode) == expected
    assert stream.tell() == 2 + len(payload)
    assert stream.read() == sentinel
