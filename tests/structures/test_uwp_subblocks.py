from struct import pack

import pytest

from pylnk3.structures.id_list.uwp import UwpSubBlock


@pytest.mark.parametrize(('text', 'payload', 'units', 'padding'), [
    ('a', b'a\x00\x00\x00', 2, b''),
    ('ab', b'a\x00b\x00\x00\x00', 3, b'\x00\x00'),
    ('é漢', b'\xe9\x00\x22\x6f\x00\x00', 3, b'\x00\x00'),
    ('😀', b'\x3d\xd8\x00\xde\x00\x00', 3, b'\x00\x00'),
    ('a😀', b'a\x00\x3d\xd8\x00\xde\x00\x00', 4, b''),
    ('😀🚀', b'\x3d\xd8\x00\xde\x3d\xd8\x80\xde\x00\x00', 5, b'\x00\x00'),
])
def test_uwp_string_layout(text: str, payload: bytes, units: int, padding: bytes) -> None:
    """Raw length and padding checks catch malformed strings that the reader otherwise accepts."""
    block = UwpSubBlock(type=0x0F, value=text)
    raw = block.bytes
    assert raw == pack('<BIII', 0x0F, 0, 0x1F, units) + payload + padding
    assert (len(raw) - 13) % 4 == 0
    assert UwpSubBlock(raw).value == text
