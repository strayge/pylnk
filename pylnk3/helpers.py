import ntpath
import re
from typing import Any, Dict, Iterable, List, Optional, Union

from pylnk3.structures import (
    DriveEntry, ExtraData, ExtraData_EnvironmentVariableDataBlock, IDListEntry, LinkInfo,
    LinkTargetIDList, Lnk, PathSegmentEntry, RootEntry, UwpSegmentEntry,
)
from pylnk3.structures.id_list.path import TYPE_FOLDER
from pylnk3.structures.id_list.root import ROOT_MY_COMPUTER, ROOT_UWP_APPS

# def is_lnk(f: BytesIO) -> bool:
#     if hasattr(f, 'name'):
#         if f.name.split(os.path.extsep)[-1] == "lnk":
#             assert_lnk_signature(f)
#             return True
#         else:
#             return False
#     else:
#         try:
#             assert_lnk_signature(f)
#             return True
#         except FormatException:
#             return False


def path_levels(p: str) -> Iterable[str]:
    dirname, base = ntpath.split(p)
    if base != '':
        yield from path_levels(dirname)
    yield p


def is_drive(data: Union[str, Any]) -> bool:
    if not isinstance(data, str):
        return False
    p = re.compile("[a-zA-Z]:\\\\?$")
    return p.match(data) is not None


def parse(lnk: str) -> Lnk:
    return Lnk(lnk)


def create(f: Optional[str] = None) -> Lnk:
    lnk = Lnk()
    lnk.file = f
    return lnk


def for_file(
    target_file: str,
    lnk_name: Optional[str] = None,
    arguments: Optional[str] = None,
    description: Optional[str] = None,
    icon_file: Optional[str] = None,
    icon_index: int = 0,
    work_dir: Optional[str] = None,
    window_mode: Optional[str] = None,
    is_file: Optional[bool] = None,
) -> Lnk:
    lnk = create(lnk_name)
    lnk.link_flags.IsUnicode = True
    lnk.link_info = None
    if target_file.startswith('\\\\'):
        # remote link
        lnk.link_info = LinkInfo()
        lnk.link_info.remote = 1
        # extract server + share name from full path
        path_parts = target_file.split('\\')
        share_name, base_name = '\\'.join(path_parts[:4]), '\\'.join(path_parts[4:])
        lnk.link_info.network_share_name = share_name.upper()
        lnk.link_info.base_name = base_name
        # somehow it requires EnvironmentVariableDataBlock & HasExpString flag
        env_data_block = ExtraData_EnvironmentVariableDataBlock()
        env_data_block.target_ansi = target_file
        env_data_block.target_unicode = target_file
        lnk.extra_data = ExtraData(blocks=[env_data_block])
        lnk.link_flags.HasExpString = True
    else:
        # local link
        levels = list(path_levels(target_file))
        elements = [
            RootEntry(ROOT_MY_COMPUTER),
            DriveEntry(levels[0]),
        ]
        for level in levels[1:]:
            is_last_level = level == levels[-1]
            # consider all segments before last as directory
            segment = PathSegmentEntry.create_for_path(level, is_file=is_file if is_last_level else False)
            elements.append(segment)
        lnk.shell_item_id_list = LinkTargetIDList()
        lnk.shell_item_id_list.items = elements
    # lnk.link_flags.HasLinkInfo = True
    if arguments:
        lnk.link_flags.HasArguments = True
        lnk.arguments = arguments
    if description:
        lnk.link_flags.HasName = True
        lnk.description = description
    if icon_file:
        lnk.link_flags.HasIconLocation = True
        lnk.icon = icon_file
    lnk.icon_index = icon_index
    if work_dir:
        lnk.link_flags.HasWorkingDir = True
        lnk.work_dir = work_dir
    if window_mode:
        lnk.window_mode = window_mode
    if lnk_name:
        lnk.save()
    return lnk


def from_segment_list(
    data: List[Union[str, Dict[str, Any]]],
    lnk_name: Optional[str] = None,
) -> Lnk:
    """
    Creates a lnk file from a list of path segments.
    If lnk_name is given, the resulting lnk will be saved
    to a file with that name.
    The expected list for has the following format ("C:\\dir\\file.txt"):

    ['c:\\',
     {'type': TYPE_FOLDER,
      'size': 0,            # optional for folders
      'name': "dir",
      'created': datetime.datetime(2012, 10, 12, 23, 28, 11, 8476),
      'modified': datetime.datetime(2012, 10, 12, 23, 28, 11, 8476),
      'accessed': datetime.datetime(2012, 10, 12, 23, 28, 11, 8476)
     },
     {'type': TYPE_FILE,
      'size': 823,
      'name': "file.txt",
      'created': datetime.datetime(2012, 10, 12, 23, 28, 11, 8476),
      'modified': datetime.datetime(2012, 10, 12, 23, 28, 11, 8476),
      'accessed': datetime.datetime(2012, 10, 12, 23, 28, 11, 8476)
     }
    ]

    For relative paths just omit the drive entry.
    Hint: Correct dates really are not crucial for working lnks.
    """
    if not isinstance(data, (list, tuple)):
        raise ValueError("Invalid data format, list or tuple expected")
    lnk = Lnk()
    entries: List[IDListEntry] = []
    if is_drive(data[0]):
        assert isinstance(data[0], str)
        # this is an absolute link
        entries.append(RootEntry(ROOT_MY_COMPUTER))
        if not data[0].endswith('\\'):
            data[0] += "\\"
        drive = data[0].encode("ascii")
        data.pop(0)
        entries.append(DriveEntry(drive))
    data_without_root: List[Dict[str, Any]] = data  # type: ignore
    for level in data_without_root:
        segment = PathSegmentEntry()
        segment.type = level['type']
        if level['type'] == TYPE_FOLDER:
            segment.file_size = 0
        else:
            segment.file_size = level['size']
        segment.short_name = level['name']
        segment.full_name = level['name']
        segment.created = level['created']
        segment.modified = level['modified']
        segment.accessed = level['accessed']
        entries.append(segment)
    lnk.shell_item_id_list = LinkTargetIDList()
    lnk.shell_item_id_list.items = entries
    if data_without_root[-1]['type'] == TYPE_FOLDER:
        lnk.file_flags.directory = True
    if lnk_name:
        lnk.save(lnk_name)
    return lnk


def build_uwp(
    package_family_name: str,
    target: str,
    location: Optional[str] = None,
    logo44x44: Optional[str] = None,
    lnk_name: Optional[str] = None,
) -> Lnk:
    """
    :param lnk_name:            ex.: crafted_uwp.lnk
    :param package_family_name: ex.: Microsoft.WindowsCalculator_10.1910.0.0_x64__8wekyb3d8bbwe
    :param target:              ex.: Microsoft.WindowsCalculator_8wekyb3d8bbwe!App
    :param location:            ex.: C:\\Program Files\\WindowsApps\\Microsoft.WindowsCalculator_10.1910.0.0_x64__8wekyb3d8bbwe
    :param logo44x44:           ex.: Assets\\CalculatorAppList.png
    """
    lnk = Lnk()
    lnk.link_flags.HasLinkTargetIDList = True
    lnk.link_flags.IsUnicode = True
    lnk.link_flags.EnableTargetMetadata = True

    lnk.shell_item_id_list = LinkTargetIDList()

    elements = [
        RootEntry(ROOT_UWP_APPS),
        UwpSegmentEntry.create(
            package_family_name=package_family_name,
            target=target,
            location=location,
            logo44x44=logo44x44,
        ),
    ]
    lnk.shell_item_id_list.items = elements

    if lnk_name:
        lnk.file = lnk_name
        lnk.save()
    return lnk
