def padding(val: bytes, size: int, byte: bytes = b'\x00') -> bytes:
    return val + (size - len(val)) * byte
