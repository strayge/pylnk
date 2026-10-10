from copy import deepcopy
from datetime import datetime
from struct import unpack_from

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


@pytest.mark.parametrize('drive', ['C:', 'c:\\'])
def test_from_segment_list_absolute_path(temp_filename: str, drive: str) -> None:
    """Textual drives must build an absolute target before and after saving the shortcut."""
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    lnk = from_segment_list([
        drive,
        {
            'type': 'FOLDER',
            'name': 'folder',
            'created': timestamp,
            'modified': timestamp,
            'accessed': timestamp,
        },
        {
            'type': 'FILE',
            'name': 'file.txt',
            'size': 823,
            'created': timestamp,
            'modified': timestamp,
            'accessed': timestamp,
        },
    ], lnk_name=temp_filename)
    assert lnk.path == r'C:\folder\file.txt'
    assert Lnk.from_file(temp_filename).path == r'C:\folder\file.txt'


@pytest.mark.parametrize('as_tuple', [False, True], ids=['list', 'tuple'])
@pytest.mark.parametrize('drive', ['C:', 'c:\\'])
def test_from_segment_list_preserves_input(drive: str, as_tuple: bool) -> None:
    """Reusing a caller-owned sequence must not remove its drive or alter its metadata."""
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    data: list[str | dict[str, object]] = [drive, {
        'type': 'FOLDER',
        'name': 'folder',
        'created': timestamp,
        'modified': timestamp,
        'accessed': timestamp,
    }]
    segments = tuple(data) if as_tuple else data
    expected = deepcopy(segments)
    for _ in range(2):
        lnk = from_segment_list(segments)
        assert segments == expected
        assert lnk.path == r'C:\folder'
        assert Lnk.from_bytes(lnk.bytes()).path == r'C:\folder'


@pytest.mark.parametrize('segment_type', ['FOLDER', 'TYPE_FOLDER'])
def test_from_segment_list_folder_without_size(segment_type: str) -> None:
    """Relative folders may omit file size without needing a drive entry."""
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    lnk = from_segment_list([
        {
            'type': segment_type,
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
    pytest.param('FOLDER', 'folder', 0, True, id='folder'),
    pytest.param('FILE', 'file.txt', 823, False, id='file'),
    pytest.param('TYPE_FOLDER', 'folder', 823, True, id='folder-alias'),
    pytest.param('TYPE_FILE', 'file.txt', 823, False, id='file-alias'),
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
    entry = lnk.shell_item_id_list.items[0]
    assert isinstance(entry, PathSegmentFileOrFolderEntry)
    assert (entry.flags.IsDirectory, entry.flags.IsFile) == (is_directory, not is_directory)
    assert entry.file_size == (0 if is_directory else size)
    assert bool(unpack_from('<H', entry.bytes, 10)[0] & 0x10) == is_directory
    assert lnk.file_flags.directory == is_directory

    parsed = Lnk.from_bytes(lnk.bytes())
    entry = parsed.shell_item_id_list.items[0]
    assert isinstance(entry, PathSegmentFileOrFolderEntry)
    assert (entry.flags.IsDirectory, entry.flags.IsFile) == (is_directory, not is_directory)
    assert parsed.file_flags.directory == is_directory


@pytest.mark.parametrize('segment_type', ['FILE', 'TYPE_FILE'])
def test_from_segment_list_file_requires_size(segment_type: str) -> None:
    """File sizes must remain explicit rather than silently defaulting to zero."""
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    with pytest.raises(KeyError, match='size'):
        from_segment_list([
            {
                'type': segment_type,
                'name': 'file.txt',
                'created': timestamp,
                'modified': timestamp,
                'accessed': timestamp,
            },
        ])


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
