import ntpath
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from pylnk3.exceptions import MissingInformationException
from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.utils.guid import bytes_from_guid, guid_from_bytes
from pylnk3.utils.read_write import (
    read_cstring, read_cunicode, read_dos_datetime, read_double, read_int, read_short,
    write_cstring, write_cunicode, write_dos_datetime, write_double, write_int, write_short,
)

_ENTRY_TYPES = {
    0x00: 'KNOWN_FOLDER',
    0x31: 'FOLDER',
    0x32: 'FILE',
    0x35: 'FOLDER (UNICODE)',
    0x36: 'FILE (UNICODE)',
    0x802E: 'ROOT_KNOWN_FOLDER',
    # founded in doc, not tested
    0x1f: 'ROOT_FOLDER',
    0x61: 'URI',
    0x71: 'CONTROL_PANEL',
}
_ENTRY_TYPE_IDS = dict((v, k) for k, v in _ENTRY_TYPES.items())

TYPE_FOLDER = 'FOLDER'
TYPE_FILE = 'FILE'


class PathSegmentEntry(IDListEntry):

    def __init__(self, bytes: Optional[bytes] = None) -> None:
        self.type = None
        self.file_size = None
        self.modified = None
        self.short_name = None
        self.created = None
        self.accessed = None
        self.full_name = None
        if bytes is None:
            return

        buf = BytesIO(bytes)
        self.type = _ENTRY_TYPES.get(read_short(buf), 'UNKNOWN')
        short_name_is_unicode = self.type.endswith('(UNICODE)')

        if self.type == 'ROOT_KNOWN_FOLDER':
            self.full_name = '::' + guid_from_bytes(buf.read(16))
            # then followed Beef0026 structure:
            # short size
            # short version
            # int signature == 0xBEEF0026
            # (16 bytes) created timestamp
            # (16 bytes) modified timestamp
            # (16 bytes) accessed timestamp
            return

        if self.type == 'KNOWN_FOLDER':
            _ = read_short(buf)  # extra block size
            extra_signature = read_int(buf)
            if extra_signature == 0x23FEBBEE:
                _ = read_short(buf)  # unknown
                _ = read_short(buf)  # guid len
                # that format recognized by explorer
                self.full_name = '::' + guid_from_bytes(buf.read(16))
            return

        self.file_size = read_int(buf)
        self.modified = read_dos_datetime(buf)
        unknown = read_short(buf)  # FileAttributesL
        if short_name_is_unicode:
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

    @classmethod
    def create_for_path(cls, path: str, is_file: Optional[bool] = None) -> 'PathSegmentEntry':
        entry = cls()
        try:
            st = os.stat(path)
            entry.file_size = st.st_size
            entry.modified = datetime.fromtimestamp(st.st_mtime)
            entry.created = datetime.fromtimestamp(st.st_ctime)
            entry.accessed = datetime.fromtimestamp(st.st_atime)
            if is_file is None:
                is_file = not os.path.isdir(path)
        except FileNotFoundError:
            now = datetime.now()
            entry.file_size = 0
            entry.modified = now
            entry.created = now
            entry.accessed = now
            if is_file is None:
                is_file = '.' in ntpath.split(path)[-1][1:]
        entry.short_name = ntpath.split(path)[1]
        entry.full_name = entry.short_name
        entry.type = TYPE_FILE if is_file else TYPE_FOLDER
        return entry

    def _validate(self) -> None:
        if self.type is None:
            raise MissingInformationException("Type is missing, choose either TYPE_FOLDER or TYPE_FILE.")
        if self.file_size is None:
            if self.type.startswith('FOLDER') or self.type in ('KNOWN_FOLDER', 'ROOT_KNOWN_FOLDER'):
                self.file_size = 0
            else:
                raise MissingInformationException("File size missing")
        if self.created is None:
            self.created = datetime.now()
        if self.modified is None:
            self.modified = datetime.now()
        if self.accessed is None:
            self.accessed = datetime.now()
        # if self.modified is None or self.accessed is None or self.created is None:
        #     raise MissingInformationException("Date information missing")
        if self.full_name is None:
            raise MissingInformationException("A full name is missing")
        if self.short_name is None:
            self.short_name = self.full_name

    @property
    def bytes(self) -> bytes:
        if self.full_name is None:
            return b''
        self._validate()

        # explicit check to have strict types without optionals
        assert self.short_name is not None
        assert self.type is not None
        assert self.file_size is not None
        assert self.modified is not None
        assert self.created is not None
        assert self.accessed is not None

        out = BytesIO()
        entry_type = self.type

        if entry_type == 'KNOWN_FOLDER':
            write_short(_ENTRY_TYPE_IDS[entry_type], out)
            write_short(0x1A, out)  # size
            write_int(0x23FEBBEE, out)  # extra signature
            write_short(0x00, out)  # extra signature
            write_short(0x10, out)  # guid size
            out.write(bytes_from_guid(self.full_name.strip(':')))
            return out.getvalue()

        if entry_type == 'ROOT_KNOWN_FOLDER':
            write_short(_ENTRY_TYPE_IDS[entry_type], out)
            out.write(bytes_from_guid(self.full_name.strip(':')))
            write_short(0x26, out)  # 0xBEEF0026 structure size
            write_short(0x01, out)  # version
            write_int(0xBEEF0026, out)  # extra signature
            write_int(0x11, out)  # some flag for containing datetime
            write_double(0x00, out)  # created datetime
            write_double(0x00, out)  # modified datetime
            write_double(0x00, out)  # accessed datetime
            write_short(0x14, out)  # unknown
            return out.getvalue()

        short_name_len = len(self.short_name) + 1
        try:
            self.short_name.encode("ascii")
            short_name_is_unicode = False
            short_name_len += short_name_len % 2  # padding
        except (UnicodeEncodeError, UnicodeDecodeError):
            short_name_is_unicode = True
            short_name_len = short_name_len * 2
            self.type += " (UNICODE)"
        write_short(_ENTRY_TYPE_IDS[entry_type], out)
        write_int(self.file_size, out)
        write_dos_datetime(self.modified, out)
        write_short(0x10, out)
        if short_name_is_unicode:
            write_cunicode(self.short_name, out)
        else:
            write_cstring(self.short_name, out, padding=True)
        indicator = 24 + 2 * len(self.short_name)
        write_short(indicator, out)  # size
        write_short(0x03, out)  # version
        write_short(0x04, out)  # signature part1
        write_short(0xBeef, out)  # signature part2
        write_dos_datetime(self.created, out)
        write_dos_datetime(self.accessed, out)
        offset_unicode = 0x14  # fixed data structure, always the same
        write_short(offset_unicode, out)
        offset_ansi = 0  # we always write unicode
        write_short(offset_ansi, out)  # long_string_size
        write_cunicode(self.full_name, out)
        offset_part2 = 0x0E + short_name_len
        write_short(offset_part2, out)
        return out.getvalue()

    def __str__(self) -> str:
        return "<PathSegmentEntry: %s>" % self.full_name
