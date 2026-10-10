import struct

import pytest

from pylnk3 import Lnk


@pytest.mark.parametrize(('icon_index', 'encoded'), [
    (-2147483648, b'\x00\x00\x00\x80'),
    (-1, b'\xff\xff\xff\xff'),
    (0, b'\x00\x00\x00\x00'),
    (2147483647, b'\xff\xff\xff\x7f'),
])
def test_icon_index_signed_layout(icon_index: int, encoded: bytes) -> None:
    """Icon resources use a signed field while the adjacent file size remains unsigned."""
    header = Lnk().bytes()
    file_size_bytes = b'\x98\xba\xdc\xfe'
    reference = header[:0x34] + file_size_bytes + encoded + header[0x3C:]
    parsed = Lnk.from_bytes(reference)
    assert parsed.icon_index == icon_index
    assert parsed.file_size == 0xFEDCBA98

    lnk = Lnk()
    lnk.file_size = 0xFEDCBA98
    lnk.icon_index = icon_index
    assert lnk.bytes()[0x34:0x3C] == file_size_bytes + encoded


@pytest.mark.parametrize('icon_index', [-2147483649, 2147483648])
def test_icon_index_rejects_out_of_range(icon_index: int) -> None:
    """Out-of-range resource identifiers must not wrap into a different signed value."""
    lnk = Lnk()
    lnk.icon_index = icon_index
    with pytest.raises(struct.error):
        lnk.bytes()
