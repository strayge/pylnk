from io import BufferedIOBase, BytesIO
from struct import unpack
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from pylnk3.utils.data import convert_time_to_unix
from pylnk3.utils.guid import guid_to_str
from pylnk3.utils.padding import padding
from pylnk3.utils.read_write import read_byte, read_int, read_short, write_int, write_short


class TypedPropertyValue:
    # types: [MS-OLEPS] section 2.15
    def __init__(
        self,
        bytes_: Optional[bytes] = None,
        type_: Optional[int] = None,
        value: Optional[bytes] = None,
    ) -> None:
        if bytes_ is not None:
            self.type: int = read_short(BytesIO(bytes_))
            padding = bytes_[2:4]
            self.value: bytes = bytes_[4:]
        elif type_ is not None and value is not None:
            self.type = type_
            self.value = value or b''
        else:
            raise ValueError("Either bytes or type and value must be given.")

    def set_string(self, value: str) -> None:
        self.type = 0x1f
        buf = BytesIO()
        write_int(len(value) + 2, buf)
        buf.write(value.encode('utf-16-le'))
        # terminator (included in size)
        buf.write(b'\x00\x00\x00\x00')
        # padding (not included in size)
        if len(value) % 2:
            buf.write(b'\x00\x00')
        self.value = buf.getvalue()

    @property
    def bytes(self) -> bytes:
        buf = BytesIO()
        write_short(self.type, buf)
        write_short(0x0000, buf)
        buf.write(self.value)
        return buf.getvalue()

    def __str__(self) -> str:
        value = self.value
        if self.type == 0x1F:
            size = value[:4]
            value_str = value[4:].decode('utf-16-le')
        elif self.type == 0x15:
            value_str = unpack('<Q', value)[0]
        elif self.type == 0x13:
            value_str = unpack('<I', value)[0]
        elif self.type == 0x14:
            value_str = unpack('<q', value)[0]
        elif self.type == 0x16:
            value_str = unpack('<i', value)[0]
        elif self.type == 0x17:
            value_str = unpack('<I', value)[0]
        elif self.type == 0x48:
            value_str = guid_to_str(value)
        elif self.type == 0x40:
            # FILETIME (Packet Version)
            stream = BytesIO(value)
            low = read_int(stream)
            high = read_int(stream)
            num = (high << 32) + low
            value_str = str(convert_time_to_unix(num))
        else:
            value_str = str(value)
        return f'{hex(self.type)}: {value_str!s}'


class PropertyStore:
    def __init__(
        self,
        bytes: Optional[BytesIO] = None,
        properties: Optional[List[Tuple[Union[str, int], TypedPropertyValue]]] = None,
        format_id: Optional[bytes] = None,
        is_strings: bool = False,
    ) -> None:
        self.is_strings = is_strings
        self.format_id = format_id or b''
        self._is_end = False
        self.properties: List[Tuple[Union[str, int], TypedPropertyValue]] = properties or []
        if bytes:
            self.read(bytes)

    def read(self, bytes_io: BytesIO) -> None:
        buf = bytes_io
        size = read_int(buf)
        assert size < len(buf.getvalue())
        if size == 0x00000000:
            self._is_end = True
            return
        version = read_int(buf)
        assert version == 0x53505331
        self.format_id = buf.read(16)
        if self.format_id == b'\xD5\xCD\xD5\x05\x2E\x9C\x10\x1B\x93\x97\x08\x00\x2B\x2C\xF9\xAE':
            self.is_strings = True
        else:
            self.is_strings = False
        while True:
            # assert lnk.tell() < (start + size)
            value_size = read_int(buf)
            if value_size == 0x00000000:
                break
            if self.is_strings:
                name_size = read_int(buf)
                _ = read_byte(buf)  # reserved
                name = buf.read(name_size).decode('utf-16-le')
                value = TypedPropertyValue(buf.read(value_size - 9))
                self.properties.append((name, value))
            else:
                value_id = read_int(buf)
                _ = read_byte(buf)  # reserved
                value = TypedPropertyValue(buf.read(value_size - 9))
                self.properties.append((value_id, value))

    @property
    def bytes(self) -> bytes:
        size = 8 + len(self.format_id)
        properties = BytesIO()
        for name, value in self.properties:
            value_bytes = value.bytes
            if self.is_strings:
                assert isinstance(name, str)
                name_bytes = name.encode('utf-16-le')
                value_size = 9 + len(name_bytes) + len(value_bytes)
                write_int(value_size, properties)
                name_size = len(name_bytes)
                write_int(name_size, properties)
                properties.write(b'\x00')
                properties.write(name_bytes)
            else:
                assert isinstance(name, int)
                value_size = 9 + len(value_bytes)
                write_int(value_size, properties)
                write_int(name, properties)
                properties.write(b'\x00')
            properties.write(value_bytes)
            size += value_size

        write_int(0x00000000, properties)
        size += 4

        buf = BytesIO()
        write_int(size, buf)
        write_int(0x53505331, buf)
        buf.write(self.format_id)
        buf.write(properties.getvalue())

        return buf.getvalue()

    def __str__(self) -> str:
        s = ' PropertyStore'
        s += '\n  FormatID: %s' % guid_to_str(self.format_id)
        for name, value in self.properties:
            s += '\n  %3s = %s' % (name, str(value))
        return s.strip()


class ExtraData_DataBlock:
    def __init__(self, bytes: Optional[bytes] = None, **kwargs: Any) -> None:
        raise NotImplementedError

    def bytes(self) -> bytes:
        raise NotImplementedError


class ExtraData_IconEnvironmentDataBlock(ExtraData_DataBlock):
    def __init__(self, bytes: Optional[bytes] = None) -> None:
        # self._size = None
        # self._signature = None
        self._signature = 0xA0000007
        self.target_ansi: str = None  # type: ignore[assignment]
        self.target_unicode: str = None  # type: ignore[assignment]
        if bytes:
            self.read(bytes)

    def read(self, bytes: bytes) -> None:
        buf = BytesIO(bytes)
        # self._size = read_int(buf)
        # self._signature = read_int(buf)
        self.target_ansi = buf.read(260).decode('ansi')
        self.target_unicode = buf.read(520).decode('utf-16-le')

    def bytes(self) -> bytes:
        target_ansi = padding(self.target_ansi.encode(), 260)
        target_unicode = padding(self.target_unicode.encode('utf-16-le'), 520)
        size = 8 + len(target_ansi) + len(target_unicode)
        assert self._signature == 0xA0000007
        assert size == 0x00000314
        buf = BytesIO()
        write_int(size, buf)
        write_int(self._signature, buf)
        buf.write(target_ansi)
        buf.write(target_unicode)
        return buf.getvalue()

    def __str__(self) -> str:
        target_ansi = self.target_ansi.replace('\x00', '')
        target_unicode = self.target_unicode.replace('\x00', '')
        s = f'IconEnvironmentDataBlock\n TargetAnsi: {target_ansi}\n TargetUnicode: {target_unicode}'
        return s


EXTRA_DATA_TYPES = {
    0xA0000002: 'ConsoleDataBlock',  # size 0x000000CC
    0xA0000004: 'ConsoleFEDataBlock',  # size 0x0000000C
    0xA0000006: 'DarwinDataBlock',  # size 0x00000314
    0xA0000001: 'EnvironmentVariableDataBlock',  # size 0x00000314
    0xA0000007: 'IconEnvironmentDataBlock',  # size 0x00000314
    0xA000000B: 'KnownFolderDataBlock',  # size 0x0000001C
    0xA0000009: 'PropertyStoreDataBlock',  # size >= 0x0000000C
    0xA0000008: 'ShimDataBlock',  # size >= 0x00000088
    0xA0000005: 'SpecialFolderDataBlock',  # size 0x00000010
    0xA0000003: 'VistaAndAboveIDListDataBlock',  # size 0x00000060
    0xA000000C: 'VistaIDListDataBlock',  # size 0x00000173
}


class ExtraData_Unparsed(ExtraData_DataBlock):
    def __init__(
        self,
        signature: int,
        bytes: Optional[bytes] = None,
        data: Optional[bytes] = None,
    ) -> None:
        self._signature = signature
        self._size = None
        if bytes is not None:
            self.data = bytes
        elif data is not None:
            self.data = data
        else:
            raise ValueError("Either bytes or data must be given.")

    # def read(self, bytes):
    #     buf = BytesIO(bytes)
    #     size = len(bytes)
    #     # self._size = read_int(buf)
    #     # self._signature = read_int(buf)
    #     self.data = buf.read(self._size - 8)

    def bytes(self) -> bytes:
        buf = BytesIO()
        write_int(len(self.data) + 8, buf)
        write_int(self._signature, buf)
        buf.write(self.data)
        return buf.getvalue()

    def __str__(self) -> str:
        s = f'ExtraDataBlock\n signature {hex(self._signature)}\n data: {self.data!r}'
        return s


class ExtraData_PropertyStoreDataBlock(ExtraData_DataBlock):
    def __init__(
        self,
        bytes: Optional[bytes] = None,
        stores: Optional[List[PropertyStore]] = None,
    ) -> None:
        self._size = None
        self._signature = 0xA0000009
        self.stores = []
        if stores:
            self.stores = stores
        if bytes:
            self.read(bytes)

    def read(self, bytes: bytes) -> None:
        buf = BytesIO(bytes)
        # self._size = read_int(buf)
        # self._signature = read_int(buf)
        # [MS-PROPSTORE] section 2.2
        while True:
            prop_store = PropertyStore(buf)
            if prop_store._is_end:
                break
            self.stores.append(prop_store)

    def bytes(self) -> bytes:
        stores = b''
        for prop_store in self.stores:
            stores += prop_store.bytes
        size = len(stores) + 8 + 4

        assert self._signature == 0xA0000009
        assert size >= 0x0000000C

        buf = BytesIO()
        write_int(size, buf)
        write_int(self._signature, buf)
        buf.write(stores)
        write_int(0x00000000, buf)
        return buf.getvalue()

    def __str__(self) -> str:
        s = 'PropertyStoreDataBlock'
        for prop_store in self.stores:
            s += '\n %s' % str(prop_store)
        return s


class ExtraData_EnvironmentVariableDataBlock(ExtraData_DataBlock):
    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self._signature = 0xA0000001
        self.target_ansi = ''
        self.target_unicode = ''
        if bytes:
            self.read(bytes)

    def read(self, bytes: bytes) -> None:
        buf = BytesIO(bytes)
        self.target_ansi = buf.read(260).decode()
        self.target_unicode = buf.read(520).decode('utf-16-le')

    def bytes(self) -> bytes:
        target_ansi = padding(self.target_ansi.encode(), 260)
        target_unicode = padding(self.target_unicode.encode('utf-16-le'), 520)
        size = 8 + len(target_ansi) + len(target_unicode)
        assert self._signature == 0xA0000001
        assert size == 0x00000314
        buf = BytesIO()
        write_int(size, buf)
        write_int(self._signature, buf)
        buf.write(target_ansi)
        buf.write(target_unicode)
        return buf.getvalue()

    def __str__(self) -> str:
        target_ansi = self.target_ansi.replace('\x00', '')
        target_unicode = self.target_unicode.replace('\x00', '')
        s = f'EnvironmentVariableDataBlock\n TargetAnsi: {target_ansi}\n TargetUnicode: {target_unicode}'
        return s


EXTRA_DATA_TYPES_CLASSES: Dict[str, Type[ExtraData_DataBlock]] = {
    'IconEnvironmentDataBlock': ExtraData_IconEnvironmentDataBlock,
    'PropertyStoreDataBlock': ExtraData_PropertyStoreDataBlock,
    'EnvironmentVariableDataBlock': ExtraData_EnvironmentVariableDataBlock,
}


class ExtraData:
    # EXTRA_DATA = *EXTRA_DATA_BLOCK TERMINAL_BLOCK
    def __init__(self, lnk: Optional[BufferedIOBase] = None, blocks: Optional[List[ExtraData_DataBlock]] = None) -> None:
        self.blocks = []
        if blocks:
            self.blocks = blocks
        if lnk is None:
            return
        while True:
            size = read_int(lnk)
            if size < 4:  # TerminalBlock
                break
            signature = read_int(lnk)
            bytes = lnk.read(size - 8)
            # lnk.seek(-8, 1)
            block_type = EXTRA_DATA_TYPES[signature]
            if block_type in EXTRA_DATA_TYPES_CLASSES:
                block_class = EXTRA_DATA_TYPES_CLASSES[block_type]
                block = block_class(bytes=bytes)
            else:
                block_class = ExtraData_Unparsed
                block = block_class(bytes=bytes, signature=signature)
            self.blocks.append(block)

    @property
    def bytes(self) -> bytes:
        result = b''
        for block in self.blocks:
            result += block.bytes()
        result += b'\x00\x00\x00\x00'  # TerminalBlock
        return result

    def __str__(self) -> str:
        s = ''
        for block in self.blocks:
            s += '\n' + str(block)
        return s
