from datetime import datetime
from io import BufferedIOBase
from struct import pack, unpack
from typing import Union

DEFAULT_CHARSET = 'cp1251'


def read_byte(buf: BufferedIOBase) -> int:
    return unpack('<B', buf.read(1))[0]  # type: ignore[no-any-return]


def read_short(buf: BufferedIOBase) -> int:
    return unpack('<H', buf.read(2))[0]  # type: ignore[no-any-return]


def read_int(buf: BufferedIOBase) -> int:
    return unpack('<I', buf.read(4))[0]  # type: ignore[no-any-return]


def read_double(buf: BufferedIOBase) -> int:
    return unpack('<Q', buf.read(8))[0]  # type: ignore[no-any-return]


def read_cunicode(buf: BufferedIOBase) -> str:
    s = b""
    b = buf.read(2)
    while b != b'\x00\x00':
        s += b
        b = buf.read(2)
    return s.decode('utf-16-le')


def read_cstring(buf: BufferedIOBase, padding: bool = False) -> str:
    s = b""
    b = buf.read(1)
    while b != b'\x00':
        s += b
        b = buf.read(1)
    if padding and not len(s) % 2:
        buf.read(1)  # make length + terminator even
    # TODO: encoding is not clear, unicode-escape has been necessary sometimes
    return s.decode(DEFAULT_CHARSET)


def read_sized_string(buf: BufferedIOBase, string: bool = True) -> Union[str, bytes]:
    size = read_short(buf)
    if string:
        return buf.read(size * 2).decode('utf-16-le')
    else:
        return buf.read(size)


def get_bits(value: int, start: int, count: int, length: int = 16) -> int:
    mask = 0
    for i in range(count):
        mask = mask | 1 << i
    shift = length - start - count
    return value >> shift & mask


def read_dos_datetime(buf: BufferedIOBase) -> datetime:
    date = read_short(buf)
    time = read_short(buf)
    year = get_bits(date, 0, 7) + 1980
    month = get_bits(date, 7, 4)
    day = get_bits(date, 11, 5)
    hour = get_bits(time, 0, 5)
    minute = get_bits(time, 5, 6)
    second = get_bits(time, 11, 5)
    # fix zeroes
    month = max(month, 1)
    day = max(day, 1)
    return datetime(year, month, day, hour, minute, second)


def write_byte(val: int, buf: BufferedIOBase) -> None:
    buf.write(pack('<B', val))


def write_short(val: int, buf: BufferedIOBase) -> None:
    buf.write(pack('<H', val))


def write_int(val: int, buf: BufferedIOBase) -> None:
    buf.write(pack('<I', val))


def write_double(val: int, buf: BufferedIOBase) -> None:
    buf.write(pack('<Q', val))


def write_cstring(val: str, buf: BufferedIOBase, padding: bool = False) -> None:
    # val = val.encode('unicode-escape').replace('\\\\', '\\')
    val_bytes = val.encode(DEFAULT_CHARSET)
    buf.write(val_bytes + b'\x00')
    if padding and not len(val_bytes) % 2:
        buf.write(b'\x00')


def write_cunicode(val: str, buf: BufferedIOBase) -> None:
    uni = val.encode('utf-16-le')
    buf.write(uni + b'\x00\x00')


def write_sized_string(val: str, buf: BufferedIOBase, string: bool = True) -> None:
    size = len(val)
    write_short(size, buf)
    if string:
        buf.write(val.encode('utf-16-le'))
    else:
        buf.write(val.encode())


def put_bits(bits: int, target: int, start: int, count: int, length: int = 16) -> int:
    return target | bits << (length - start - count)


def write_dos_datetime(val: datetime, buf: BufferedIOBase) -> None:
    date = time = 0
    date = put_bits(val.year - 1980, date, 0, 7)
    date = put_bits(val.month, date, 7, 4)
    date = put_bits(val.day, date, 11, 5)
    time = put_bits(val.hour, time, 0, 5)
    time = put_bits(val.minute, time, 5, 6)
    time = put_bits(val.second, time, 11, 5)
    write_short(date, buf)
    write_short(time, buf)
