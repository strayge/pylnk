import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest

from pylnk3.utils.read_write import read_cstring, read_cunicode


@pytest.mark.parametrize(('reader', 'payload'), [
    ('read_cstring', b''),
    ('read_cstring', b'abc'),
    ('read_cunicode', b''),
    ('read_cunicode', b'\x00'),
    ('read_cunicode', b'A\x00'),
    ('read_cunicode', b'A\x00\x00'),
])
def test_unterminated_cstring_raises(reader: str, payload: bytes) -> None:
    """A regressed EOF loop must fail within a deadline rather than hang the test runner."""
    code = (
        'from io import BytesIO\n'
        f'from pylnk3.utils.read_write import {reader}\n'
        'try:\n'
        f'    {reader}(BytesIO({payload!r}))\n'
        'except EOFError:\n'
        '    pass\n'
        'else:\n'
        '    raise AssertionError("Unterminated strings must raise EOFError")\n'
    )
    subprocess.run(
        [sys.executable, '-c', code], check=True, capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[2], timeout=5,
    )


@pytest.mark.parametrize(('unicode', 'payload', 'expected'), [
    (False, b'\x00', ''),
    (False, b'abc\x00', 'abc'),
    (True, b'\x00\x00', ''),
    (True, b'A\x00\x3d\xd8\x00\xde\x00\x00', 'A😀'),
])
def test_terminated_cstring_boundary(unicode: bool, payload: bytes, expected: str) -> None:
    """EOF guards must leave valid terminators and the following field's bytes intact."""
    sentinel = b'\xff\x00\x00'
    stream = BytesIO(payload + sentinel)
    reader = read_cunicode if unicode else read_cstring
    assert reader(stream) == expected
    assert stream.tell() == len(payload)
    assert stream.read() == sentinel


def test_terminated_invalid_utf16_raises() -> None:
    """A present terminator must not conceal an invalid UTF-16 surrogate sequence."""
    with pytest.raises(UnicodeDecodeError):
        read_cunicode(BytesIO(b'\x3d\xd8\x00\x00'))
