from io import BufferedIOBase
from typing import Optional

from pylnk3.exceptions import MissingInformationException
from pylnk3.utils.read_write import read_cstring, read_int, write_byte, write_cstring, write_int

DRIVE_NO_ROOT_DIR = "No root directory"
DRIVE_REMOVABLE = "Removable"
DRIVE_FIXED = "Fixed (Hard disk)"
DRIVE_REMOTE = "Remote (Network drive)"
DRIVE_CDROM = "CD-ROM"
DRIVE_RAMDISK = "Ram disk"
DRIVE_UNKNOWN = "Unknown"

_DRIVE_TYPES = {
    0: DRIVE_UNKNOWN,
    1: DRIVE_NO_ROOT_DIR,
    2: DRIVE_REMOVABLE,
    3: DRIVE_FIXED,
    4: DRIVE_REMOTE,
    5: DRIVE_CDROM,
    6: DRIVE_RAMDISK,
}
_DRIVE_TYPE_IDS = dict((v, k) for k, v in _DRIVE_TYPES.items())

_LINK_INFO_HEADER_DEFAULT = 0x1C
_LINK_INFO_HEADER_OPTIONAL = 0x24


class LinkInfo:

    def __init__(self, lnk: Optional[BufferedIOBase] = None) -> None:
        if lnk is not None:
            self.start = lnk.tell()
            self.size = read_int(lnk)
            self.header_size = read_int(lnk)
            link_info_flags = read_int(lnk)
            self.local = link_info_flags & 1
            self.remote = link_info_flags & 2
            self.offs_local_volume_table = read_int(lnk)
            self.offs_local_base_path = read_int(lnk)
            self.offs_network_volume_table = read_int(lnk)
            self.offs_base_name = read_int(lnk)
            if self.header_size >= _LINK_INFO_HEADER_OPTIONAL:
                print("TODO: read the unicode stuff")  # TODO: read the unicode stuff
            self._parse_path_elements(lnk)
        else:
            self.size = 0
            self.header_size = _LINK_INFO_HEADER_DEFAULT
            self.local = 0
            self.remote = 0
            self.offs_local_volume_table = 0
            self.offs_local_base_path = 0
            self.offs_network_volume_table = 0
            self.offs_base_name = 0
            self.drive_type: Optional[str] = None
            self.drive_serial: int = None  # type: ignore[assignment]
            self.volume_label: str = None  # type: ignore[assignment]
            self.local_base_path: str = None  # type: ignore[assignment]
            self.network_share_name: str = ''
            self.base_name: str = ''
            self._path: str = ''

    def _parse_path_elements(self, lnk: BufferedIOBase) -> None:
        if self.remote:
            # 20 is the offset of the network share name
            lnk.seek(self.start + self.offs_network_volume_table + 20)
            self.network_share_name = read_cstring(lnk)
            lnk.seek(self.start + self.offs_base_name)
            self.base_name = read_cstring(lnk)
        if self.local:
            lnk.seek(self.start + self.offs_local_volume_table + 4)
            self.drive_type = _DRIVE_TYPES.get(read_int(lnk))
            self.drive_serial = read_int(lnk)
            lnk.read(4)  # volume name offset (10h)
            self.volume_label = read_cstring(lnk)
            lnk.seek(self.start + self.offs_local_base_path)
            self.local_base_path = read_cstring(lnk)
            # TODO: unicode
        self.make_path()

    def make_path(self) -> None:
        if self.remote:
            self._path = self.network_share_name + '\\' + self.base_name
        if self.local:
            self._path = self.local_base_path

    def write(self, lnk: BufferedIOBase) -> None:
        if self.remote is None:
            raise MissingInformationException("No location information given.")
        self.start = lnk.tell()
        self._calculate_sizes_and_offsets()
        write_int(self.size, lnk)
        write_int(self.header_size, lnk)
        write_int((self.local and 1) + (self.remote and 2), lnk)
        write_int(self.offs_local_volume_table, lnk)
        write_int(self.offs_local_base_path, lnk)
        write_int(self.offs_network_volume_table, lnk)
        write_int(self.offs_base_name, lnk)
        if self.remote:
            self._write_network_volume_table(lnk)
            write_cstring(self.base_name, lnk, padding=False)
        else:
            self._write_local_volume_table(lnk)
            write_cstring(self.local_base_path, lnk, padding=False)
            write_byte(0, lnk)

    def _calculate_sizes_and_offsets(self) -> None:
        self.size_base_name = 1  # len(self.base_name) + 1  # zero terminated strings
        self.size = 28 + self.size_base_name
        if self.remote:
            self.size_network_volume_table = 20 + len(self.network_share_name) + len(self.base_name) + 1
            self.size += self.size_network_volume_table
            self.offs_local_volume_table = 0
            self.offs_local_base_path = 0
            self.offs_network_volume_table = 28
            self.offs_base_name = self.offs_network_volume_table + self.size_network_volume_table
        else:
            self.size_local_volume_table = 16 + len(self.volume_label) + 1
            self.size_local_base_path = len(self.local_base_path) + 1
            self.size += self.size_local_volume_table + self.size_local_base_path
            self.offs_local_volume_table = 28
            self.offs_local_base_path = self.offs_local_volume_table + self.size_local_volume_table
            self.offs_network_volume_table = 0
            self.offs_base_name = self.offs_local_base_path + self.size_local_base_path

    def _write_network_volume_table(self, buf: BufferedIOBase) -> None:
        write_int(self.size_network_volume_table, buf)
        write_int(2, buf)  # ?
        write_int(20, buf)  # size of Network Volume Table
        write_int(0, buf)  # ?
        write_int(131072, buf)  # ?
        write_cstring(self.network_share_name, buf)

    def _write_local_volume_table(self, buf: BufferedIOBase) -> None:
        write_int(self.size_local_volume_table, buf)
        if self.drive_type is None or self.drive_type not in _DRIVE_TYPE_IDS:
            raise ValueError("This is not a valid drive type: %s" % self.drive_type)
        drive_type = _DRIVE_TYPE_IDS[self.drive_type]
        write_int(drive_type, buf)
        write_int(self.drive_serial, buf)
        write_int(16, buf)  # volume name offset
        write_cstring(self.volume_label, buf)

    @property
    def path(self) -> str:
        return self._path

    def __str__(self) -> str:
        s = "File Location Info:"
        if not self._path:
            return s + " <not specified>"
        if self.remote:
            s += "\n  (remote)"
            s += "\n  Network Share: %s" % self.network_share_name
            s += "\n  Base Name: %s" % self.base_name
        else:
            s += "\n  (local)"
            s += "\n  Volume Type: %s" % self.drive_type
            s += "\n  Volume Serial Number: %s" % self.drive_serial
            s += "\n  Volume Label: %s" % self.volume_label
            s += "\n  Path: %s" % self.local_base_path
        return s
