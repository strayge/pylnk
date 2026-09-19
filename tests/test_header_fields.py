import io
from datetime import datetime
from struct import pack

import pytest

from pylnk3 import Lnk, convert_time_to_unix

# Minimal well-formed shell link: 76-byte header plus an EXTRA_DATA terminal block.
# No IDList, no LinkInfo, no StringData -- enough to exercise the header fields.
LINK_CLSID = bytes(
    [0x01, 0x14, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00,
     0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46]
)
# 2026-03-14 09:15:30 UTC as a FILETIME
SAMPLE_FILETIME = 134179533300000000


def _build_lnk(icon_index: int = 0, write_time: int = SAMPLE_FILETIME) -> bytes:
    header = bytearray(0x4C)
    header[0x00:0x04] = pack('<I', 0x4C)
    header[0x04:0x14] = LINK_CLSID
    header[0x14:0x18] = pack('<I', 0x00000080)          # IsUnicode only
    header[0x18:0x1C] = pack('<I', 0x00000020)          # FILE_ATTRIBUTE_ARCHIVE
    header[0x1C:0x24] = pack('<Q', SAMPLE_FILETIME)     # CreationTime
    header[0x24:0x2C] = pack('<Q', SAMPLE_FILETIME)     # AccessTime
    header[0x2C:0x34] = pack('<Q', write_time)          # WriteTime
    header[0x34:0x38] = pack('<I', 1024)                # FileSize
    header[0x38:0x3C] = pack('<i', icon_index)          # IconIndex (signed)
    header[0x3C:0x40] = pack('<I', 1)                   # ShowCommand
    return bytes(header) + pack('<I', 0)                # EXTRA_DATA terminal block


def test_out_of_range_filetime_returns_none():
    """An unrepresentable FILETIME must not be replaced with a synthesised time.

    Previously this returned datetime.now() on platforms where
    datetime.fromtimestamp raises OSError (Windows), making a corrupt timestamp
    indistinguishable from a genuine one.
    """
    assert convert_time_to_unix(0xFFFFFFFFFFFFFFFF) is None


def test_out_of_range_filetime_is_deterministic():
    """Same input, same answer. A clock-derived fallback fails this."""
    assert convert_time_to_unix(0xFFFFFFFFFFFFFFFF) == convert_time_to_unix(
        0xFFFFFFFFFFFFFFFF
    )


def test_corrupt_write_time_does_not_yield_current_time():
    lnk = Lnk(io.BytesIO(_build_lnk(write_time=0xFFFFFFFFFFFFFFFF)))
    assert lnk.modification_time is None
    # Undamaged fields in the same file still parse.
    assert isinstance(lnk.creation_time, datetime)


@pytest.mark.parametrize('icon_index', (-1, -7, 0, 3, 2147483647))
def test_icon_index_is_signed(icon_index: int):
    """IconIndex is a signed 32-bit integer per MS-SHLLINK section 2.1."""
    lnk = Lnk(io.BytesIO(_build_lnk(icon_index=icon_index)))
    assert lnk.icon_index == icon_index


def test_negative_icon_index_round_trip():
    """Saving a link with a negative icon index previously raised struct.error."""
    lnk = Lnk(io.BytesIO(_build_lnk(icon_index=-7)))
    out = io.BytesIO()
    lnk.write(out)
    assert Lnk(io.BytesIO(out.getvalue())).icon_index == -7
