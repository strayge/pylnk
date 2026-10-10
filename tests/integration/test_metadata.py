import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from struct import unpack_from

import pytest

from pylnk3 import Lnk
from pylnk3.structures.extra_data import (
    ExtraData_EnvironmentVariableDataBlock, ExtraData_IconEnvironmentDataBlock,
    ExtraData_PropertyStoreDataBlock, ExtraData_Unparsed,
)
from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.structures.id_list.drive import DriveEntry
from pylnk3.structures.id_list.path import (
    PathSegmentEntry, PathSegmentFileOrFolderEntry, PathSegmentKnownFolderEntry,
    PathSegmentRootKnownFolderEntry,
)
from pylnk3.structures.id_list.root import RootEntry
from pylnk3.structures.id_list.uwp import UwpSegmentEntry

_FIXTURE_NAMES = tuple(
    path.name for path in sorted((Path(__file__).parents[1] / 'data').glob('*.lnk'))
)
assert _FIXTURE_NAMES, 'The integration corpus must not silently collect zero cases.'


@pytest.mark.parametrize('filename', _FIXTURE_NAMES)
def test_header_semantics_survive_roundtrip(examples_path: str, filename: str) -> None:
    """A correct target alone does not establish preservation of shortcut metadata."""
    original = Lnk.from_file(str(Path(examples_path) / filename))
    fields = (
        'description', 'relative_path', 'work_dir', 'arguments', 'icon',
        'window_mode', 'hot_key', 'file_size', 'icon_index',
    )
    expected = {field: getattr(original, field) for field in fields}
    file_flags = original.file_flags.bytes
    # StringData may switch encoding without changing its decoded values.
    semantic_flags_mask = ~(1 << 7)
    link_flags = original.link_flags.bytes & semantic_flags_mask
    restored = Lnk.from_bytes(original.bytes())
    assert {field: getattr(restored, field) for field in fields} == expected
    assert restored.file_flags.bytes == file_flags
    assert restored.link_flags.bytes & semantic_flags_mask == link_flags


@pytest.mark.parametrize('filename', _FIXTURE_NAMES)
def test_link_info_semantics_survive_roundtrip(examples_path: str, filename: str) -> None:
    """Alternate path representations must not disappear behind the selected target."""
    original = Lnk.from_file(str(Path(examples_path) / filename))
    fields = ['local', 'remote']
    if original.link_info.local:
        fields.extend((
            'drive_type', 'drive_serial', 'volume_label', 'local_base_path',
            'local_base_path_unicode', 'local_base_path_suffix_unicode',
        ))
    if original.link_info.remote:
        fields.append('network_share_name')
    expected = {field: getattr(original.link_info, field) for field in fields}
    restored = Lnk.from_bytes(original.bytes())
    assert {field: getattr(restored.link_info, field) for field in fields} == expected


@pytest.mark.parametrize(
    'filename', tuple(name for name in _FIXTURE_NAMES if name.startswith(('net_', 'mounted_'))),
)
def test_network_link_info_suffix_survives_roundtrip(examples_path: str, filename: str) -> None:
    """Mounted links can retain their selected target while losing the network path."""
    original = Lnk.from_file(str(Path(examples_path) / filename))
    expected_suffix = original.link_info.base_name
    restored = Lnk.from_bytes(original.bytes())
    assert restored.link_info.base_name == expected_suffix


@pytest.mark.parametrize('filename', _FIXTURE_NAMES)
def test_extra_data_semantics_survive_roundtrip(examples_path: str, filename: str) -> None:
    """Known values and opaque payloads must survive independently of binary packing."""
    original = Lnk.from_file(str(Path(examples_path) / filename))
    expected_extra = deepcopy(original.extra_data)
    restored = Lnk.from_bytes(original.bytes())
    assert expected_extra is not None
    assert restored.extra_data is not None
    assert len(restored.extra_data.blocks) == len(expected_extra.blocks)
    for before, after in zip(expected_extra.blocks, restored.extra_data.blocks, strict=True):
        assert type(after) is type(before)
        if isinstance(before, ExtraData_Unparsed):
            assert isinstance(after, ExtraData_Unparsed)
            assert after._signature == before._signature
            assert after.data == before.data
        elif isinstance(before, (ExtraData_EnvironmentVariableDataBlock, ExtraData_IconEnvironmentDataBlock)):
            assert isinstance(after, (ExtraData_EnvironmentVariableDataBlock, ExtraData_IconEnvironmentDataBlock))
            assert after.target_ansi.rstrip('\x00') == before.target_ansi.rstrip('\x00')
            assert after.target_unicode.rstrip('\x00') == before.target_unicode.rstrip('\x00')
        elif isinstance(before, ExtraData_PropertyStoreDataBlock):
            assert isinstance(after, ExtraData_PropertyStoreDataBlock)
            assert len(after.stores) == len(before.stores)
            for old_store, new_store in zip(before.stores, after.stores, strict=True):
                assert new_store.format_id == old_store.format_id
                assert new_store.is_strings == old_store.is_strings
                assert len(new_store.properties) == len(old_store.properties)
                for (old_name, old_value), (new_name, new_value) in zip(
                    old_store.properties, new_store.properties, strict=True,
                ):
                    assert new_name == old_name
                    assert new_value.type == old_value.type
                    if old_value.type == 0x1F:
                        assert new_value.value[4:].decode('utf-16-le').rstrip('\x00') == (
                            old_value.value[4:].decode('utf-16-le').rstrip('\x00')
                        )
                    else:
                        assert new_value.value == old_value.value
        else:
            pytest.fail('Add semantic expectations for this newly supported extra-data block.')


def _shell_item_semantics(item: IDListEntry) -> dict[str, object]:
    """Capture immutable values before serialization can normalize a mutable segment."""
    values: dict[str, object] = {'class': type(item)}
    if isinstance(item, PathSegmentFileOrFolderEntry):
        fields = ('file_size', 'created', 'modified', 'accessed', 'short_name', 'full_name', 'localized_name')
        values.update({field: getattr(item, field) for field in fields})
        values.update(is_file=item.flags.IsFile, is_directory=item.flags.IsDirectory)
    elif isinstance(item, RootEntry):
        values.update(guid=item.guid, root=item.root)
    elif isinstance(item, DriveEntry):
        values['drive'] = item.drive
    elif isinstance(item, (PathSegmentKnownFolderEntry, PathSegmentRootKnownFolderEntry)):
        values['guid'] = item.guid
    elif type(item) is PathSegmentEntry:
        values['raw'] = item.raw
    elif isinstance(item, UwpSegmentEntry):
        values['blocks'] = tuple(
            (block.guid, tuple((sub_block.type, sub_block.value) for sub_block in block._blocks))
            for block in item._blocks
        )
    else:
        pytest.fail('Add semantic expectations for this newly supported shell item.')
    return values


@pytest.mark.parametrize('filename', _FIXTURE_NAMES)
def test_shell_item_metadata_survives_roundtrip(examples_path: str, filename: str) -> None:
    """Preserve names, classification and segment metadata beyond the assembled target."""
    original = Lnk.from_file(str(Path(examples_path) / filename))
    if not original.link_flags.HasLinkTargetIDList:
        restored = Lnk.from_bytes(original.bytes())
        assert not restored.link_flags.HasLinkTargetIDList
        return
    expected = [_shell_item_semantics(item) for item in original.shell_item_id_list.items]
    restored = Lnk.from_bytes(original.bytes())
    assert [_shell_item_semantics(item) for item in restored.shell_item_id_list.items] == expected


def test_localized_names_survive_roundtrip(examples_path: str) -> None:
    """Explorer display-name references are supported metadata, not disposable padding."""
    original = Lnk.from_file(str(Path(examples_path) / 'local_emoji.lnk'))
    expected = [
        item.localized_name for item in original.shell_item_id_list.items
        if isinstance(item, PathSegmentFileOrFolderEntry)
    ]
    assert expected == [None, '@shell32.dll,-21816', None, None]
    restored = Lnk.from_bytes(original.bytes())
    assert [
        item.localized_name for item in restored.shell_item_id_list.items
        if isinstance(item, PathSegmentFileOrFolderEntry)
    ] == expected


@pytest.mark.xfail(
    sys.platform in ('darwin', 'win32'), strict=True, raises=AssertionError,
    reason='Unrepresentable FILETIME epoch values are replaced with current timestamps.',
)
def test_unset_timestamps_survive_roundtrip(examples_path: str) -> None:
    """Zero FILETIMEs are valid unset values and must not become current file activity."""
    data = (Path(examples_path) / 'uwp_calc.lnk').read_bytes()
    expected = unpack_from('<3Q', data, 0x1C)
    restored_data = Lnk.from_bytes(data).bytes()
    assert unpack_from('<3Q', restored_data, 0x1C) == expected


@pytest.mark.parametrize(
    'timestamp',
    (
        datetime(2024, 1, 15, 12, 30, 40),
        pytest.param(
            datetime(2024, 1, 15, 12, 30, 40, 123456),
            marks=pytest.mark.xfail(
                strict=True, raises=AssertionError,
                reason='FILETIME serialization drops datetime microseconds.',
            ),
        ),
    ),
    ids=('whole-seconds', 'microseconds'),
)
def test_timestamps_survive_roundtrip(timestamp: datetime) -> None:
    """Timestamp precision is semantic data, not an allowed layout normalization."""
    original = Lnk()
    original.creation_time = timestamp
    original.access_time = timestamp + timedelta(seconds=1)
    original.modification_time = timestamp + timedelta(seconds=2)
    expected = (original.creation_time, original.access_time, original.modification_time)
    restored = Lnk.from_bytes(original.bytes())
    assert (restored.creation_time, restored.access_time, restored.modification_time) == expected
