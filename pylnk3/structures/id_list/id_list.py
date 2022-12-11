from io import BytesIO
from typing import List, Optional

from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.structures.id_list.drive import DriveEntry
from pylnk3.structures.id_list.path import PathSegmentEntry
from pylnk3.structures.id_list.root import ROOT_MY_COMPUTER, ROOT_NETWORK_PLACES, RootEntry
from pylnk3.structures.id_list.uwp import UwpSegmentEntry
from pylnk3.utils.read_write import read_short, write_short


class LinkTargetIDList:

    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self.items: List[IDListEntry] = []
        if bytes is not None:
            buf = BytesIO(bytes)
            raw = []
            entry_len = read_short(buf)
            while entry_len > 0:
                raw.append(buf.read(entry_len - 2))  # the length includes the size
                entry_len = read_short(buf)
            self._interpret(raw)

    def _interpret(self, raw: Optional[List[bytes]]) -> None:
        if not raw:
            return
        elif raw[0][0] == 0x1F:
            root_entry = RootEntry(raw[0])
            self.items.append(root_entry)
            if root_entry.root == ROOT_MY_COMPUTER:
                if len(raw[1]) == 0x17:
                    self.items.append(DriveEntry(raw[1]))
                elif raw[1][0:2] == b'\x2E\x80':  # ROOT_KNOWN_FOLDER
                    self.items.append(PathSegmentEntry(raw[1]))
                else:
                    raise ValueError("This seems to be an absolute link which requires a drive as second element.")
                items = raw[2:]
            elif root_entry.root == ROOT_NETWORK_PLACES:
                raise NotImplementedError(
                    "Parsing network lnks has not yet been implemented. "
                    "If you need it just contact me and we'll see...",
                )
            else:
                items = raw[1:]
        else:
            items = raw
        for item in items:
            if item[4:8] == b'APPS':
                self.items.append(UwpSegmentEntry(item))
            else:
                self.items.append(PathSegmentEntry(item))

    def get_path(self) -> str:
        segments: List[str] = []
        for item in self.items:
            if type(item) == RootEntry:
                segments.append('%' + item.root + '%')
            elif type(item) == DriveEntry:
                segments.append(item.drive.decode())
            elif type(item) == PathSegmentEntry:
                if item.full_name is not None:
                    segments.append(item.full_name)
            else:
                segments.append(str(item))
        return '\\'.join(segments)

    def _validate(self) -> None:
        if not len(self.items):
            return
        root_entry = self.items[0]
        if isinstance(root_entry, RootEntry) and root_entry.root == ROOT_MY_COMPUTER:
            second_entry = self.items[1]
            if isinstance(second_entry, DriveEntry):
                return
            if (
                isinstance(second_entry, PathSegmentEntry)
                and second_entry.full_name is not None
                and second_entry.full_name.startswith('::')
            ):
                return
            raise ValueError("A drive is required for absolute lnks")

    @property
    def bytes(self) -> bytes:
        self._validate()
        out = BytesIO()
        for item in self.items:
            bytes = item.bytes
            write_short(len(bytes) + 2, out)  # len + terminator
            out.write(bytes)
        out.write(b'\x00\x00')
        return out.getvalue()

    def __str__(self) -> str:
        string = '<LinkTargetIDList>:\n'
        for item in self.items:
            string += f'  {item}\n'
        return string.strip()
