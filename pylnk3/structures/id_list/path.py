import ntpath
import os
from binascii import hexlify
from datetime import datetime
from io import BytesIO
from typing import Optional

from pylnk3.exceptions import MissingInformationException
from pylnk3.flags import Flags
from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.utils.guid import bytes_from_guid, guid_from_bytes
from pylnk3.utils.read_write import (
    read_cstring, read_cunicode, read_dos_datetime, read_double, read_int, read_short,
    write_cstring, write_cunicode, write_dos_datetime, write_double, write_int, write_short,
)

_ENTRY_TYPES = {
    0x00: 'KNOWN_FOLDER',
    0x30: 'FILE_OR_FOLDER',  # all 0x3x variations
    0x802E: 'ROOT_KNOWN_FOLDER',
    # founded in doc, not tested
    0x1f: 'ROOT_FOLDER',
    0x61: 'URI',
    0x71: 'CONTROL_PANEL',
}
_ENTRY_TYPE_IDS = dict((v, k) for k, v in _ENTRY_TYPES.items())

_FILE_OR_FOLDER_ENTRY_FLAGS = (
    'IsDirectory',
    'IsFile',
    'IsUnicode',
)


class FileOrFolderEntryFlags(Flags):
    def __init__(self, flags_bytes: int = 0) -> None:
        super().__init__(_FILE_OR_FOLDER_ENTRY_FLAGS, flags_bytes)


class PathSegmentEntry(IDListEntry):
    def __init__(self, bytes: Optional[bytes] = None) -> None:
        if bytes is None:
            return

        self.raw = bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PathSegmentEntry':
        first_word: int = int.from_bytes(data[0:2], byteorder='little')
        if (first_word & 0xFFFF0) == _ENTRY_TYPE_IDS['FILE_OR_FOLDER']:
            return PathSegmentFileOrFolderEntry(data)
        if first_word == _ENTRY_TYPE_IDS['KNOWN_FOLDER']:
            return PathSegmentKnownFolderEntry(data)
        if first_word == _ENTRY_TYPE_IDS['ROOT_KNOWN_FOLDER']:
            return PathSegmentRootKnownFolderEntry(data)
        return cls(data)

    @property
    def path(self) -> str:
        return '<UNKNOWN>'

    @property
    def bytes(self) -> bytes:
        return self.raw

    def __str__(self) -> str:
        return "<PathSegmentEntry: %s>" % str(self.raw)

    def json(self) -> dict:
        return {
            'class': 'PathSegmentEntry',
            'raw': hexlify(self.raw).decode(),
        }


class PathSegmentFileOrFolderEntry(PathSegmentEntry):
    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self.type = 'FILE_OR_FOLDER'
        self.flags = FileOrFolderEntryFlags()

        self.file_size = None
        self.modified = None
        self.created = None
        self.accessed = None
        self.short_name = None
        self.full_name = None
        self.localized_name = None

        if bytes is None:
            return

        buf = BytesIO(bytes)

        type_and_flags = read_short(buf)
        type_id = type_and_flags & 0xFFF0
        assert type_id == _ENTRY_TYPE_IDS[self.type]

        self.flags = FileOrFolderEntryFlags(type_and_flags & 0x000F)

        self.file_size = read_int(buf)
        self.modified = read_dos_datetime(buf)
        unknown = read_short(buf)  # FileAttributesL
        if self.flags.IsUnicode:
            self.short_name = read_cunicode(buf)
        else:
            self.short_name = read_cstring(buf, padding=True)
        extra_size = read_short(buf)
        extra_version = read_short(buf)
        extra_signature = read_int(buf)
        if extra_signature == 0xBEEF0004:
            # indicator_1 = read_short(buf)  # see below
            # only_83 = read_short(buf) < 0x03
            # unknown = read_short(buf)  # 0x04
            # self.is_unicode = read_short(buf) == 0xBeef
            self.created = read_dos_datetime(buf)  # 4 bytes
            self.accessed = read_dos_datetime(buf)  # 4 bytes
            offset_unicode = read_short(buf)   # offset from start of extra_size
            # only_83_2 = offset_unicode >= indicator_1 or offset_unicode < 0x14
            if extra_version >= 7:
                offset_ansi = read_short(buf)
                file_reference = read_double(buf)
                unknown2 = read_double(buf)
            long_string_size = 0
            if extra_version >= 3:
                long_string_size = read_short(buf)
            if extra_version >= 9:
                unknown4 = read_int(buf)
            if extra_version >= 8:
                unknown5 = read_int(buf)
            if extra_version >= 3:
                self.full_name = read_cunicode(buf)
                if long_string_size > 0:
                    if extra_version >= 7:
                        self.localized_name = read_cunicode(buf)
                    else:
                        self.localized_name = read_cstring(buf)
                version_offset = read_short(buf)

    @property
    def bytes(self) -> bytes:
        self._validate()
        # explicit check to have strict types without optionals
        assert self.short_name is not None
        assert self.full_name is not None
        assert self.modified is not None
        assert self.created is not None
        assert self.accessed is not None
        assert self.file_size is not None

        out = BytesIO()
        short_name_len = len(self.short_name) + 1
        try:
            self.flags.IsUnicode = False
            self.short_name.encode("ascii")
            short_name_len += short_name_len % 2  # padding
        except (UnicodeEncodeError, UnicodeDecodeError):
            self.flags.IsUnicode = True
            short_name_len = short_name_len * 2

        type_and_flags = _ENTRY_TYPE_IDS[self.type] | self.flags.bytes
        write_short(type_and_flags, out)
        write_int(self.file_size, out)
        write_dos_datetime(self.modified, out)
        write_short(0x10, out)
        if self.flags.IsUnicode:
            write_cunicode(self.short_name, out)
        else:
            write_cstring(self.short_name, out, padding=True)

        version = 3  # just hardcode some version
        # structures below compatible with versions 3 and 9 in case someone needs it

        # offset from start of size field until start of full_name
        if version == 9:
            offset_unicode = 0x2E
        elif version == 3:
            offset_unicode = 0x14
        else:
            raise NotImplementedError("Other versions not implemented yet")

        size = offset_unicode + 2 * (len(self.full_name) + 2) + 2  # full struct size
        write_short(size, out)  # size
        write_short(version, out)  # version
        write_int(0xBEEF0004, out)  # signature
        write_dos_datetime(self.created, out)
        write_dos_datetime(self.accessed, out)
        write_short(offset_unicode, out)
        if version >= 9:
            write_short(0, out)  # offset_ansi
            write_double(0, out)  # file_reference
            write_double(0, out)  # unknown2
        offset_ansi = 0  # we always write unicode
        write_short(offset_ansi, out)  # long_string_size
        if version >= 9:
            write_int(0, out)  # unknown4
            write_int(0, out)  # unknown5
        write_cunicode(self.full_name, out)
        offset_part2 = 0x0E + short_name_len
        write_short(offset_part2, out)
        return out.getvalue()

    @property
    def path(self) -> str:
        return self.full_name or ''

    def _validate(self) -> None:
        if self.type is None:
            raise MissingInformationException("Type is missing")
        if self.file_size is None:
            self.file_size = 0
        if self.created is None:
            self.created = datetime.now()
        if self.modified is None:
            self.modified = datetime.now()
        if self.accessed is None:
            self.accessed = datetime.now()
        if self.full_name is None:
            raise MissingInformationException("A full name is missing")
        if self.short_name is None:
            self.short_name = self.full_name

    @classmethod
    def create_for_path(cls, path: str, is_file: Optional[bool] = None) -> 'PathSegmentFileOrFolderEntry':
        entry = cls()

        fs_stat = None
        try:
            fs_stat = os.stat(path)
            if is_file is None:
                is_file = not os.path.isdir(path)
        except OSError:  # ex.: not found or path too long
            pass

        if fs_stat:
            entry.file_size = fs_stat.st_size
            entry.modified = datetime.fromtimestamp(fs_stat.st_mtime)
            entry.created = datetime.fromtimestamp(fs_stat.st_ctime)
            entry.accessed = datetime.fromtimestamp(fs_stat.st_atime)
        else:
            now = datetime.now()
            entry.file_size = 0
            entry.modified = now
            entry.created = now
            entry.accessed = now

        if is_file is None:
            is_file = '.' in ntpath.split(path)[-1][1:]

        entry.short_name = ntpath.split(path)[1]
        entry.full_name = entry.short_name
        if is_file:
            entry.flags.IsFile = True
        else:
            entry.flags.IsDirectory = True
        return entry

    def __str__(self) -> str:
        return "<PathSegmentFileOrFolderEntry: %s>" % self.full_name

    def json(self) -> dict:
        return {
            'class': 'PathSegmentFileOrFolderEntry',
            'file_size': self.file_size,
            'modified': self.modified.isoformat() if self.modified else None,
            'created': self.created.isoformat() if self.created else None,
            'accessed': self.accessed.isoformat() if self.accessed else None,
            'short_name': self.short_name,
            'full_name': self.full_name,
            'flags': self.flags.json(),
        }


class PathSegmentKnownFolderEntry(PathSegmentEntry):
    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self.type = 'KNOWN_FOLDER'

        if bytes is None:
            return

        buf = BytesIO(bytes)
        type_id = read_short(buf)
        assert type_id == _ENTRY_TYPE_IDS[self.type]

        _ = read_short(buf)  # extra block size
        extra_signature = read_int(buf)
        if extra_signature == 0x23FEBBEE:
            _ = read_short(buf)  # unknown
            _ = read_short(buf)  # guid len
            # that format recognized by explorer
            self.guid = '::' + guid_from_bytes(buf.read(16))

    @property
    def bytes(self) -> bytes:
        self._validate()
        out = BytesIO()
        write_short(_ENTRY_TYPE_IDS[self.type], out)
        write_short(0x1A, out)  # size
        write_int(0x23FEBBEE, out)  # extra signature
        write_short(0x00, out)  # unknown
        write_short(0x10, out)  # guid size
        out.write(bytes_from_guid(self.guid.strip(':')))
        return out.getvalue()

    @property
    def path(self) -> str:
        return self.guid

    def _validate(self) -> None:
        if self.type is None:
            raise MissingInformationException("Type is missing")
        if self.guid is None:
            raise MissingInformationException("GUID is missing")

    def __str__(self) -> str:
        return "<PathSegmentKnownFolderEntry: %s>" % self.guid

    def json(self) -> dict:
        return {
            'class': 'PathSegmentKnownFolderEntry',
            'type': self.type,
            'guid': self.guid,
        }


class PathSegmentRootKnownFolderEntry(PathSegmentEntry):
    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self.type = 'ROOT_KNOWN_FOLDER'

        if bytes is None:
            return

        buf = BytesIO(bytes)
        type_id = read_short(buf)
        assert type_id == _ENTRY_TYPE_IDS[self.type]

        self.guid = '::' + guid_from_bytes(buf.read(16))
        # then followed Beef0026 structure:
        # short size
        # short version
        # int signature == 0xBEEF0026
        # (16 bytes) created timestamp
        # (16 bytes) modified timestamp
        # (16 bytes) accessed timestamp

    @property
    def bytes(self) -> bytes:
        self._validate()
        out = BytesIO()
        write_short(_ENTRY_TYPE_IDS[self.type], out)
        out.write(bytes_from_guid(self.guid.strip(':')))
        write_short(0x26, out)  # 0xBEEF0026 structure size
        write_short(0x01, out)  # version
        write_int(0xBEEF0026, out)  # extra signature
        write_int(0x11, out)  # some flag for containing datetime
        write_double(0x00, out)  # created datetime
        write_double(0x00, out)  # modified datetime
        write_double(0x00, out)  # accessed datetime
        write_short(0x14, out)  # unknown
        return out.getvalue()

    @property
    def path(self) -> str:
        return self.guid

    def _validate(self) -> None:
        if self.type is None:
            raise MissingInformationException("Type is missing")
        if self.guid is None:
            raise MissingInformationException("GUID is missing")

    def __str__(self) -> str:
        return "<PathSegmentRootKnownFolderEntry: %s>" % self.guid

    def json(self) -> dict:
        return {
            'class': 'PathSegmentRootKnownFolderEntry',
            'type': self.type,
            'guid': self.guid,
        }
