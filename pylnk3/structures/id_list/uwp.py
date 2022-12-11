from io import BytesIO
from typing import List, Optional, Union

from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.utils.guid import bytes_from_guid, guid_from_bytes
from pylnk3.utils.read_write import (
    read_byte, read_cunicode, read_int, read_short, write_byte, write_cunicode, write_int,
    write_short,
)


class UwpSubBlock:

    block_names = {
        0x11: 'PackageFamilyName',
        # 0x0e: '',
        # 0x19: '',
        0x15: 'PackageFullName',
        0x05: 'Target',
        0x0f: 'Location',
        0x20: 'RandomGuid',
        0x0c: 'Square150x150Logo',
        0x02: 'Square44x44Logo',
        0x0d: 'Wide310x150Logo',
        # 0x04: '',
        # 0x05: '',
        0x13: 'Square310x310Logo',
        # 0x0e: '',
        0x0b: 'DisplayName',
        0x14: 'Square71x71Logo',
        0x64: 'RandomByte',
        0x0a: 'DisplayName',
        # 0x07: '',
    }

    block_types = {
        'string': [0x11, 0x15, 0x05, 0x0f, 0x0c, 0x02, 0x0d, 0x13, 0x0b, 0x14, 0x0a],
    }

    def __init__(
        self,
        bytes: Optional[bytes] = None,
        type: Optional[int] = None,
        value: Optional[Union[str, bytes]] = None,
    ) -> None:
        if type is None and bytes is None:
            raise ValueError("Either bytes or type must be set")
        self._data = bytes or b''
        self.value = value
        if type is not None:
            self.type = type
            self.name = self.block_names.get(self.type, 'UNKNOWN')
        if not bytes:
            return
        buf = BytesIO(bytes)
        self.type = read_byte(buf)
        self.name = self.block_names.get(self.type, 'UNKNOWN')

        self.value = self._data[1:]  # skip type
        if self.type in self.block_types['string']:
            unknown = read_int(buf)
            probably_type = read_int(buf)
            if probably_type == 0x1f:
                string_len = read_int(buf)
                self.value = read_cunicode(buf)

    def __str__(self) -> str:
        string = f'UwpSubBlock {self.name} ({hex(self.type)}): {self.value!r}'
        return string.strip()

    @property
    def bytes(self) -> bytes:
        out = BytesIO()
        if self.value:
            if isinstance(self.value, str):
                string_len = len(self.value) + 1

                write_byte(self.type, out)
                write_int(0, out)
                write_int(0x1f, out)

                write_int(string_len, out)
                write_cunicode(self.value, out)
                if string_len % 2 == 1:  # padding
                    write_short(0, out)

            elif isinstance(self.value, bytes):
                write_byte(self.type, out)
                out.write(self.value)

        result = out.getvalue()
        return result


class UwpMainBlock:
    magic = b'\x31\x53\x50\x53'

    def __init__(
        self,
        bytes: Optional[bytes] = None,
        guid: Optional[str] = None,
        blocks: Optional[List[UwpSubBlock]] = None,
    ) -> None:
        self._data = bytes or b''
        self._blocks = blocks or []
        if guid is not None:
            self.guid: str = guid
        if not bytes:
            return
        buf = BytesIO(bytes)
        magic = buf.read(4)
        self.guid = guid_from_bytes(buf.read(16))
        # read sub blocks
        while True:
            sub_block_size = read_int(buf)
            if not sub_block_size:  # last size is zero
                break
            sub_block_data = buf.read(sub_block_size - 4)  # includes block_size
            self._blocks.append(UwpSubBlock(sub_block_data))

    def __str__(self) -> str:
        string = f'<UwpMainBlock> {self.guid}:\n'
        for block in self._blocks:
            string += f'      {block}\n'
        return string.strip()

    @property
    def bytes(self) -> bytes:
        blocks_bytes = [block.bytes for block in self._blocks]
        out = BytesIO()
        out.write(self.magic)
        out.write(bytes_from_guid(self.guid))
        for block in blocks_bytes:
            write_int(len(block) + 4, out)
            out.write(block)
        write_int(0, out)
        result = out.getvalue()
        return result


class UwpSegmentEntry(IDListEntry):
    magic = b'APPS'
    header = b'\x08\x00\x03\x00\x00\x00\x00\x00\x00\x00'

    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self._blocks = []
        self._data = bytes
        if bytes is None:
            return
        buf = BytesIO(bytes)
        unknown = read_short(buf)
        size = read_short(buf)
        magic = buf.read(4)  # b'APPS'
        blocks_size = read_short(buf)
        unknown2 = buf.read(10)
        # read main blocks
        while True:
            block_size = read_int(buf)
            if not block_size:  # last size is zero
                break
            block_data = buf.read(block_size - 4)  # includes block_size
            self._blocks.append(UwpMainBlock(block_data))

    def __str__(self) -> str:
        string = '<UwpSegmentEntry>:\n'
        for block in self._blocks:
            string += f'    {block}\n'
        return string.strip()

    @property
    def bytes(self) -> bytes:
        blocks_bytes = [block.bytes for block in self._blocks]
        blocks_size = sum([len(block) + 4 for block in blocks_bytes]) + 4   # with terminator
        size = (
            2  # size
            + len(self.magic)
            + 2  # second size
            + len(self.header)
            + blocks_size  # blocks with terminator
        )

        out = BytesIO()
        write_short(0, out)
        write_short(size, out)
        out.write(self.magic)
        write_short(blocks_size, out)
        out.write(self.header)
        for block in blocks_bytes:
            write_int(len(block) + 4, out)
            out.write(block)
        write_int(0, out)  # empty block
        write_short(0, out)  # ??

        result = out.getvalue()
        return result

    @classmethod
    def create(
        cls,
        package_family_name: str,
        target: str,
        location: Optional[str] = None,
        logo44x44: Optional[str] = None,
    ) -> 'UwpSegmentEntry':
        segment = cls()

        blocks = [
            UwpSubBlock(type=0x11, value=package_family_name),
            UwpSubBlock(type=0x0e, value=b'\x00\x00\x00\x00\x13\x00\x00\x00\x02\x00\x00\x00'),
            UwpSubBlock(type=0x05, value=target),
        ]
        if location:
            blocks.append(UwpSubBlock(type=0x0f, value=location))  # need for relative icon path
        main1 = UwpMainBlock(guid='{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}', blocks=blocks)
        segment._blocks.append(main1)

        if logo44x44:
            main2 = UwpMainBlock(
                guid='{86D40B4D-9069-443C-819A-2A54090DCCEC}',
                blocks=[UwpSubBlock(type=0x02, value=logo44x44)],
            )
            segment._blocks.append(main2)

        return segment
