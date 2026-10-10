import struct
from io import BytesIO

import pytest

from pylnk3.structures.extra_data import ExtraData


@pytest.mark.parametrize('terminal', [b'', b'\x00' * 4], ids=['clean-eof', 'terminal-block'])
@pytest.mark.parametrize('blocks', [b'', struct.pack('<II', 11, 0xA0000042) + b'abc'], ids=['empty', 'opaque-block'])
def test_extra_data_boundary_eof(blocks: bytes, terminal: bytes) -> None:
    """Windows-readable shortcuts may end at a block boundary without an explicit terminal block."""
    extra = ExtraData(BytesIO(blocks + terminal))
    assert extra.bytes == blocks + b'\x00' * 4


@pytest.mark.parametrize(('data', 'error'), [
    (b'\x00', struct.error),
    (b'\x00\x00\x00', struct.error),
    (struct.pack('<I', 8) + b'\x00\x00\x00', struct.error),
    (struct.pack('<I', 4), ValueError),
    (struct.pack('<II', 12, 0xA0000042) + b'ab', EOFError),
])
def test_extra_data_incomplete_block_rejected(data: bytes, error: type[Exception]) -> None:
    """Accepting clean EOF must not turn a partially present block into apparently valid data."""
    with pytest.raises(error):
        ExtraData(BytesIO(data))
