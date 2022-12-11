from datetime import datetime
from io import BufferedIOBase
from typing import Optional, Union

from pylnk3.exceptions import FormatException, InvalidKeyException
from pylnk3.flags import Flags, ModifierKeys
from pylnk3.structures.extra_data import ExtraData, ExtraData_EnvironmentVariableDataBlock
from pylnk3.structures.id_list.id_list import LinkTargetIDList
from pylnk3.structures.link_info import DRIVE_UNKNOWN, LinkInfo
from pylnk3.utils.data import convert_time_to_unix, convert_time_to_windows
from pylnk3.utils.read_write import (
    read_byte, read_double, read_int, read_short, read_sized_string, write_byte, write_double,
    write_int, write_short, write_sized_string,
)

_SIGNATURE = b'L\x00\x00\x00'
_GUID = b'\x01\x14\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00F'

_LINK_FLAGS = (
    'HasLinkTargetIDList',
    'HasLinkInfo',
    'HasName',
    'HasRelativePath',
    'HasWorkingDir',
    'HasArguments',
    'HasIconLocation',
    'IsUnicode',
    'ForceNoLinkInfo',
    # new
    'HasExpString',
    'RunInSeparateProcess',
    'Unused1',
    'HasDarwinID',
    'RunAsUser',
    'HasExpIcon',
    'NoPidlAlias',
    'Unused2',
    'RunWithShimLayer',
    'ForceNoLinkTrack',
    'EnableTargetMetadata',
    'DisableLinkPathTracking',
    'DisableKnownFolderTracking',
    'DisableKnownFolderAlias',
    'AllowLinkToLink',
    'UnaliasOnSave',
    'PreferEnvironmentPath',
    'KeepLocalIDListForUNCTarget',
)

_FILE_ATTRIBUTES_FLAGS = (
    'read_only', 'hidden', 'system_file', 'reserved1',
    'directory', 'archive', 'reserved2', 'normal',
    'temporary', 'sparse_file', 'reparse_point',
    'compressed', 'offline', 'not_content_indexed',
    'encrypted',
)

WINDOW_NORMAL = "Normal"
WINDOW_MAXIMIZED = "Maximized"
WINDOW_MINIMIZED = "Minimized"


_SHOW_COMMANDS = {1: WINDOW_NORMAL, 3: WINDOW_MAXIMIZED, 7: WINDOW_MINIMIZED}
_SHOW_COMMAND_IDS = dict((v, k) for k, v in _SHOW_COMMANDS.items())

_KEYS = {
    0x30: '0', 0x31: '1', 0x32: '2', 0x33: '3', 0x34: '4', 0x35: '5', 0x36: '6',
    0x37: '7', 0x38: '8', 0x39: '9', 0x41: 'A', 0x42: 'B', 0x43: 'C', 0x44: 'D',
    0x45: 'E', 0x46: 'F', 0x47: 'G', 0x48: 'H', 0x49: 'I', 0x4A: 'J', 0x4B: 'K',
    0x4C: 'L', 0x4D: 'M', 0x4E: 'N', 0x4F: 'O', 0x50: 'P', 0x51: 'Q', 0x52: 'R',
    0x53: 'S', 0x54: 'T', 0x55: 'U', 0x56: 'V', 0x57: 'W', 0x58: 'X', 0x59: 'Y',
    0x5A: 'Z', 0x70: 'F1', 0x71: 'F2', 0x72: 'F3', 0x73: 'F4', 0x74: 'F5',
    0x75: 'F6', 0x76: 'F7', 0x77: 'F8', 0x78: 'F9', 0x79: 'F10', 0x7A: 'F11',
    0x7B: 'F12', 0x7C: 'F13', 0x7D: 'F14', 0x7E: 'F15', 0x7F: 'F16', 0x80: 'F17',
    0x81: 'F18', 0x82: 'F19', 0x83: 'F20', 0x84: 'F21', 0x85: 'F22', 0x86: 'F23',
    0x87: 'F24', 0x90: 'NUM LOCK', 0x91: 'SCROLL LOCK',
}
_KEY_CODES = dict((v, k) for k, v in _KEYS.items())


def assert_lnk_signature(f: BufferedIOBase) -> None:
    f.seek(0)
    sig = f.read(4)
    guid = f.read(16)
    if sig != _SIGNATURE:
        raise FormatException("This is not a .lnk file.")
    if guid != _GUID:
        raise FormatException("Cannot read this kind of .lnk file.")


class Lnk:

    def __init__(self, f: Optional[Union[str, BufferedIOBase]] = None) -> None:
        self.file: Optional[str] = None
        if isinstance(f, str):
            self.file = f
            try:
                f = open(self.file, 'rb')
            except IOError:
                self.file += ".lnk"
                f = open(self.file, 'rb')
        # defaults
        self.link_flags = Flags(_LINK_FLAGS)
        self.file_flags = Flags(_FILE_ATTRIBUTES_FLAGS)
        self.creation_time = datetime.now()
        self.access_time = datetime.now()
        self.modification_time = datetime.now()
        self.file_size = 0
        self.icon_index = 0
        self._show_command = WINDOW_NORMAL
        self.hot_key: Optional[str] = None
        self._link_info = LinkInfo()
        self.description = None
        self.relative_path = None
        self.work_dir = None
        self.arguments = None
        self.icon = None
        self.extra_data: Optional[ExtraData] = None
        if f is not None:
            assert_lnk_signature(f)
            self._parse_lnk_file(f)
            f.close()

    def _read_hot_key(self, lnk: BufferedIOBase) -> str:
        low = read_byte(lnk)
        high = read_byte(lnk)
        key = _KEYS.get(low, '')
        modifier = high and str(ModifierKeys(high)) or ''
        return modifier + key

    def _write_hot_key(self, hot_key: Optional[str], lnk: BufferedIOBase) -> None:
        if hot_key is None or not hot_key:
            low = high = 0
        else:
            hot_key_parts = hot_key.split('+')
            try:
                low = _KEY_CODES[hot_key_parts[-1]]
            except KeyError:
                raise InvalidKeyException("Cannot find key code for %s" % hot_key_parts[1])
            modifiers = ModifierKeys()
            for modifier in hot_key_parts[:-1]:
                modifiers[modifier.upper()] = True
            high = modifiers.bytes
        write_byte(low, lnk)
        write_byte(high, lnk)

    def _parse_lnk_file(self, lnk: BufferedIOBase) -> None:
        # SHELL_LINK_HEADER [LINKTARGET_IDLIST] [LINKINFO] [STRING_DATA] *EXTRA_DATA

        # SHELL_LINK_HEADER
        lnk.seek(20)  # after signature and guid
        self.link_flags.set_flags(read_int(lnk))
        self.file_flags.set_flags(read_int(lnk))
        self.creation_time = convert_time_to_unix(read_double(lnk))
        self.access_time = convert_time_to_unix(read_double(lnk))
        self.modification_time = convert_time_to_unix(read_double(lnk))
        self.file_size = read_int(lnk)
        self.icon_index = read_int(lnk)
        show_command = read_int(lnk)
        self._show_command = _SHOW_COMMANDS[show_command] if show_command in _SHOW_COMMANDS else _SHOW_COMMANDS[1]
        self.hot_key = self._read_hot_key(lnk)
        lnk.read(10)  # reserved (0)

        # LINKTARGET_IDLIST (HasLinkTargetIDList)
        if self.link_flags.HasLinkTargetIDList:
            shell_item_id_list_size = read_short(lnk)
            self.shell_item_id_list = LinkTargetIDList(lnk.read(shell_item_id_list_size))

        # LINKINFO (HasLinkInfo)
        if self.link_flags.HasLinkInfo and not self.link_flags.ForceNoLinkInfo:
            self._link_info = LinkInfo(lnk)
            lnk.seek(self._link_info.start + self._link_info.size)

        # STRING_DATA = [NAME_STRING] [RELATIVE_PATH] [WORKING_DIR] [COMMAND_LINE_ARGUMENTS] [ICON_LOCATION]
        if self.link_flags.HasName:
            self.description = read_sized_string(lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasRelativePath:
            self.relative_path = read_sized_string(lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasWorkingDir:
            self.work_dir = read_sized_string(lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasArguments:
            self.arguments = read_sized_string(lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasIconLocation:
            self.icon = read_sized_string(lnk, self.link_flags.IsUnicode)

        # *EXTRA_DATA
        self.extra_data = ExtraData(lnk)

    def save(self, f: Optional[Union[str, BufferedIOBase]] = None, force_ext: bool = False) -> None:
        f = f or self.file
        is_opened_here = False
        if isinstance(f, str):
            filename: str = f
            if force_ext and not filename.endswith('.lnk'):
                filename += '.lnk'
            f = open(filename, 'wb')
            is_opened_here = True
        if f is None:
            raise ValueError("No file specified for saving LNK file")
        self.write(f)
        # only close the stream if it's our own
        if is_opened_here:
            f.close()

    def write(self, lnk: BufferedIOBase) -> None:
        lnk.write(_SIGNATURE)
        lnk.write(_GUID)
        write_int(self.link_flags.bytes, lnk)
        write_int(self.file_flags.bytes, lnk)
        write_double(convert_time_to_windows(self.creation_time), lnk)
        write_double(convert_time_to_windows(self.access_time), lnk)
        write_double(convert_time_to_windows(self.modification_time), lnk)
        write_int(self.file_size, lnk)
        write_int(self.icon_index, lnk)
        write_int(_SHOW_COMMAND_IDS[self._show_command], lnk)
        self._write_hot_key(self.hot_key, lnk)
        lnk.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')  # reserved
        if self.link_flags.HasLinkTargetIDList:
            shell_item_id_list = self.shell_item_id_list.bytes
            write_short(len(shell_item_id_list), lnk)
            lnk.write(shell_item_id_list)
        if self.link_flags.HasLinkInfo:
            self._link_info.write(lnk)
        if self.link_flags.HasName:
            write_sized_string(self.description, lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasRelativePath:
            write_sized_string(self.relative_path, lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasWorkingDir:
            write_sized_string(self.work_dir, lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasArguments:
            write_sized_string(self.arguments, lnk, self.link_flags.IsUnicode)
        if self.link_flags.HasIconLocation:
            write_sized_string(self.icon, lnk, self.link_flags.IsUnicode)
        if self.extra_data:
            lnk.write(self.extra_data.bytes)
        else:
            lnk.write(b'\x00\x00\x00\x00')

    def _get_shell_item_id_list(self) -> LinkTargetIDList:
        return self._shell_item_id_list

    def _set_shell_item_id_list(self, shell_item_id_list: LinkTargetIDList) -> None:
        self._shell_item_id_list = shell_item_id_list
        self.link_flags.HasLinkTargetIDList = shell_item_id_list is not None
    shell_item_id_list = property(_get_shell_item_id_list, _set_shell_item_id_list)

    def _get_link_info(self) -> LinkInfo:
        return self._link_info

    def _set_link_info(self, link_info: LinkInfo) -> None:
        self._link_info = link_info
        self.link_flags.ForceNoLinkInfo = link_info is None
        self.link_flags.HasLinkInfo = link_info is not None
    link_info = property(_get_link_info, _set_link_info)

    def _get_description(self) -> str:
        return self._description

    def _set_description(self, description: str) -> None:
        self._description = description
        self.link_flags.HasName = description is not None
    description = property(_get_description, _set_description)

    def _get_relative_path(self) -> str:
        return self._relative_path

    def _set_relative_path(self, relative_path: str) -> None:
        self._relative_path = relative_path
        self.link_flags.HasRelativePath = relative_path is not None
    relative_path = property(_get_relative_path, _set_relative_path)

    def _get_work_dir(self) -> str:
        return self._work_dir

    def _set_work_dir(self, work_dir: str) -> None:
        self._work_dir = work_dir
        self.link_flags.HasWorkingDir = work_dir is not None
    work_dir = working_dir = property(_get_work_dir, _set_work_dir)

    def _get_arguments(self) -> str:
        return self._arguments

    def _set_arguments(self, arguments: str) -> None:
        self._arguments = arguments
        self.link_flags.HasArguments = arguments is not None
    arguments = property(_get_arguments, _set_arguments)

    def _get_icon(self) -> str:
        return self._icon

    def _set_icon(self, icon: str) -> None:
        self._icon = icon
        self.link_flags.HasIconLocation = icon is not None
    icon = property(_get_icon, _set_icon)

    def _get_window_mode(self) -> str:
        return self._show_command

    def _set_window_mode(self, value: str) -> None:
        if value not in list(_SHOW_COMMANDS.values()):
            raise ValueError("Not a valid window mode: %s. Choose any of pylnk.WINDOW_*" % value)
        self._show_command = value
    window_mode = show_command = property(_get_window_mode, _set_window_mode)

    @property
    def path(self) -> str:
        # lnk can contains several different paths at different structures
        # here is some logic consistent with link properties at explorer (at least on test examples)

        link_info_path = self._link_info.path if self._link_info and self._link_info.path else None
        id_list_path = self._shell_item_id_list.get_path() if hasattr(self, '_shell_item_id_list') else None

        env_var_path = None
        if self.extra_data and self.extra_data.blocks:
            for block in self.extra_data.blocks:
                if type(block) == ExtraData_EnvironmentVariableDataBlock:
                    env_var_path = block.target_unicode.strip('\x00') or block.target_ansi.strip('\x00')
                    break

        if id_list_path and id_list_path.startswith('%MY_COMPUTER%'):
            # full local path has priority
            return id_list_path[14:]
        if id_list_path and id_list_path.startswith('%USERPROFILE%\\::'):
            # path to KNOWN_FOLDER also has priority over link_info
            return id_list_path[14:]
        if link_info_path:
            # local path at link_info_path has priority over network path at id_list_path
            # full local path at link_info_path has priority over partial path at id_list_path
            return link_info_path
        if env_var_path:
            # some links in Recent folder contains path only at ExtraData_EnvironmentVariableDataBlock
            return env_var_path
        return str(id_list_path)

    def specify_local_location(
        self,
        path: str,
        drive_type: Optional[str] = None,
        drive_serial: Optional[int] = None,
        volume_label: Optional[str] = None,
    ) -> None:
        self._link_info.drive_type = drive_type or DRIVE_UNKNOWN
        self._link_info.drive_serial = drive_serial or 0
        self._link_info.volume_label = volume_label or ''
        self._link_info.local_base_path = path
        self._link_info.local = True
        self._link_info.make_path()

    def specify_remote_location(self, network_share_name: str, base_name: str) -> None:
        self._link_info.network_share_name = network_share_name
        self._link_info.base_name = base_name
        self._link_info.remote = True
        self._link_info.make_path()

    def __str__(self) -> str:
        s = "Target file:\n"
        s += str(self.file_flags)
        s += "\nCreation Time: %s" % self.creation_time
        s += "\nModification Time: %s" % self.modification_time
        s += "\nAccess Time: %s" % self.access_time
        s += "\nFile size: %s" % self.file_size
        s += "\nWindow mode: %s" % self._show_command
        s += "\nHotkey: %s\n" % self.hot_key
        s += str(self._link_info)
        if self.link_flags.HasLinkTargetIDList:
            s += "\n%s" % self.shell_item_id_list
        if self.link_flags.HasName:
            s += "\nDescription: %s" % self.description
        if self.link_flags.HasRelativePath:
            s += "\nRelative Path: %s" % self.relative_path
        if self.link_flags.HasWorkingDir:
            s += "\nWorking Directory: %s" % self.work_dir
        if self.link_flags.HasArguments:
            s += "\nCommandline Arguments: %s" % self.arguments
        if self.link_flags.HasIconLocation:
            s += "\nIcon: %s" % self.icon
        if self._link_info:
            s += "\nUsed Path: %s" % self.path
        if self.extra_data:
            s += str(self.extra_data)
        return s
