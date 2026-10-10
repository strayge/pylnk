from datetime import datetime

import pytest

from pylnk3 import Lnk, for_file, from_segment_list
from pylnk3.structures import PathSegmentFileOrFolderEntry


def test_helpers_for_file(temp_filename: str) -> None:
    """A local target path survives saving and parsing the helper result."""
    path = 'C:\\folder\\file.txt'
    lnk = for_file(path)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path


@pytest.mark.xfail(
    strict=True,
    raises=KeyError,
    reason="Documented FOLDER segments incorrectly require a size key",
)
def test_from_segment_list_folder_without_size() -> None:
    """Relative folders may omit file size without needing a drive entry."""
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    lnk = from_segment_list([
        {
            'type': 'FOLDER',
            'name': 'folder',
            'created': timestamp,
            'modified': timestamp,
            'accessed': timestamp,
        },
    ])
    parsed = Lnk.from_bytes(lnk.bytes())
    assert parsed.path == 'folder'
    entry = parsed.shell_item_id_list.items[0]
    assert isinstance(entry, PathSegmentFileOrFolderEntry)
    assert entry.file_size == 0


@pytest.mark.parametrize('segment_type, name, size, is_directory', [
    pytest.param(
        'FOLDER', 'folder', 0, True,
        id='folder',
        marks=pytest.mark.xfail(
            strict=True,
            raises=AssertionError,
            reason="FOLDER segments do not set the serialized IsDirectory flag",
        ),
    ),
    pytest.param(
        'FILE', 'file.txt', 823, False,
        id='file',
        marks=pytest.mark.xfail(
            strict=True,
            raises=AssertionError,
            reason="FILE segments do not set the serialized IsFile flag",
        ),
    ),
])
def test_from_segment_list_type_flags(
    segment_type: str, name: str, size: int, is_directory: bool,
) -> None:
    """An explicit size must not erase the caller's folder or file classification."""
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    lnk = from_segment_list([
        {
            'type': segment_type,
            'size': size,
            'name': name,
            'created': timestamp,
            'modified': timestamp,
            'accessed': timestamp,
        },
    ])
    parsed = Lnk.from_bytes(lnk.bytes())
    entry = parsed.shell_item_id_list.items[0]
    assert isinstance(entry, PathSegmentFileOrFolderEntry)
    assert (entry.flags.IsDirectory, entry.flags.IsFile) == (is_directory, not is_directory)


@pytest.mark.parametrize('name, is_file', [
    pytest.param('extensionless', True, id='extensionless-file'),
    pytest.param('folder.with.dot', False, id='dotted-directory'),
])
def test_for_file_explicit_type_override(name: str, is_file: bool) -> None:
    """Explicit target types override name heuristics without reclassifying parents."""
    path = f'C:\\folder\\{name}'
    parsed = Lnk.from_bytes(for_file(path, is_file=is_file).bytes())
    assert parsed.path == path
    parent, target = parsed.shell_item_id_list.items[-2:]
    assert isinstance(parent, PathSegmentFileOrFolderEntry)
    assert isinstance(target, PathSegmentFileOrFolderEntry)
    assert (parent.flags.IsDirectory, parent.flags.IsFile) == (True, False)
    assert (target.flags.IsDirectory, target.flags.IsFile) == (not is_file, is_file)
