import json
from datetime import datetime
from pathlib import Path
from struct import pack

import pytest

from pylnk3 import Lnk, for_file
from pylnk3.utils import read_write


@pytest.mark.parametrize('filename', [
    'desktop.lnk',
    'local_disk.lnk',
    'local_emoji.lnk',
    'local_extra_0xa2000001.lnk',
    'local_file.lnk',
    'local_folder.lnk',
    'local_thispc.lnk',
    'mounted_folder1_file1.lnk',
    'mounted_folder1_file2.lnk',
    'mounted_folder2_file1.lnk',
    'mounted_folder2_file2.lnk',
    'net_folder1_file1.lnk',
    'net_folder1_file2.lnk',
    'net_folder2_file1.lnk',
    'net_folder2_file2.lnk',
    'recent1.lnk',
    'recent2.lnk',
    'send_to_fax.lnk',
    'uwp_calc.lnk',
])
def test_parse_as_json(examples_path: str, filename: str) -> None:
    """Each checked-in shortcut exposes JSON-compatible public sections."""
    lnk = Lnk.from_file(str(Path(examples_path) / filename))
    result = json.loads(json.dumps(lnk.json()))
    assert 'shell_item_id_list' in result
    assert result['window_mode'] in ('Normal', 'Maximized', 'Minimized')
    assert isinstance(result['link_flags'], dict)
    assert isinstance(result['file_flags'], dict)
    if not result['link_flags']['HasLinkTargetIDList']:
        assert result['shell_item_id_list'] is None


@pytest.mark.parametrize('parsed', [False, True], ids=['constructed', 'parsed'])
def test_json_absent_optional_sections(parsed: bool) -> None:
    """Absent sections remain distinguishable from populated optional data."""
    lnk = Lnk()
    timestamp = datetime(2020, 6, 8, 10, 12, 14)
    lnk.creation_time = lnk.access_time = lnk.modification_time = timestamp
    if parsed:
        lnk = Lnk.from_bytes(lnk.bytes())
    result = json.loads(json.dumps(lnk.json()))
    for field, flag in (
        ('description', 'HasName'),
        ('relative_path', 'HasRelativePath'),
        ('work_dir', 'HasWorkingDir'),
        ('arguments', 'HasArguments'),
        ('icon', 'HasIconLocation'),
        ('shell_item_id_list', 'HasLinkTargetIDList'),
    ):
        assert result[field] is None
        assert result['link_flags'][flag] is False
    assert result['link_flags']['HasLinkInfo'] is False
    assert result['link_info'] == {
        'remote': False,
        'network_share_name': None,
        'base_name': None,
        'drive_type': None,
        'drive_serial': None,
        'volume_label': None,
        'local_base_path': None,
        'local_base_path_unicode': None,
    }
    assert result['extra_data'] == ([] if parsed else None)
    assert result['window_mode'] == 'Normal'
    assert result['file_size'] == 0
    for field in ('creation_time', 'access_time', 'modification_time'):
        assert result[field] == '2020-06-08T10:12:14'


def test_json_present_optional_sections() -> None:
    """Populated strings, remote LinkInfo and ExtraData retain their meaningful values."""
    path = '\\\\server\\share\\file.txt'
    lnk = for_file(
        path,
        description='Shared document',
        arguments='--read-only',
        work_dir='C:\\work',
        icon_file='C:\\icons\\document.ico',
        window_mode='Maximized',
    )
    lnk.relative_path = '..\\file.txt'
    result = json.loads(json.dumps(lnk.json()))
    for field, flag, expected in (
        ('description', 'HasName', 'Shared document'),
        ('relative_path', 'HasRelativePath', '..\\file.txt'),
        ('work_dir', 'HasWorkingDir', 'C:\\work'),
        ('arguments', 'HasArguments', '--read-only'),
        ('icon', 'HasIconLocation', 'C:\\icons\\document.ico'),
    ):
        assert result[field] == expected
        assert result['link_flags'][flag] is True
    assert result['window_mode'] == 'Maximized'
    assert result['link_flags']['HasLinkInfo'] is True
    assert result['link_info']['remote'] is True
    assert result['link_info']['network_share_name'] == '\\\\SERVER\\SHARE'
    assert result['link_info']['base_name'] == 'file.txt'
    assert result['shell_item_id_list'] is None
    assert result['link_flags']['HasExpString'] is True
    assert result['extra_data'] == [{
        'class': 'EnvironmentVariableDataBlock',
        'target_ansi': path,
        'target_unicode': path,
    }]


def test_json_direct_local_helper() -> None:
    """A local helper result must be JSON-compatible before any binary roundtrip."""
    lnk = for_file('C:\\folder\\file.txt')
    result = json.loads(json.dumps(lnk.json()))
    assert result['link_info'] is None
    assert result['link_flags']['HasLinkTargetIDList'] is True
    assert result['shell_item_id_list']['items'][-1]['full_name'] == 'file.txt'


def test_json_parsed_local_helper() -> None:
    """Parsed local shortcuts expose target segments even without a LinkInfo section."""
    lnk = Lnk.from_bytes(for_file('C:\\folder\\file.txt').bytes())
    result = json.loads(json.dumps(lnk.json()))
    assert result['link_flags']['HasLinkInfo'] is False
    assert result['link_flags']['HasLinkTargetIDList'] is True
    segments = result['shell_item_id_list']['items'][-2:]
    assert [segment['full_name'] for segment in segments] == ['folder', 'file.txt']
    assert segments[0]['flags']['IsDirectory'] is True
    assert segments[1]['flags']['IsFile'] is True


def test_json_parsed_ansi_description() -> None:
    """A valid ANSI description should be exposed as JSON text rather than bytes."""
    lnk = Lnk()
    lnk.link_flags.IsUnicode = False
    lnk.description = 'hello'
    parsed = Lnk.from_bytes(lnk.bytes())
    result = json.loads(json.dumps(parsed.json()))
    assert result['description'] == 'hello'
    assert result['link_flags']['IsUnicode'] is False


@pytest.mark.parametrize(('field', 'flag', 'flag_bits'), [
    ('description', 'HasName', 0x04),
    ('relative_path', 'HasRelativePath', 0x08),
    ('work_dir', 'HasWorkingDir', 0x10),
    ('arguments', 'HasArguments', 0x20),
    ('icon', 'HasIconLocation', 0x40),
])
def test_json_raw_ansi_stringdata(
    monkeypatch: pytest.MonkeyPatch, field: str, flag: str, flag_bits: int,
) -> None:
    """JSON uses the current charset strictly without changing parsed bytes or flags."""
    header = Lnk().bytes()[:76]
    payload = b'caf\xe9'
    raw = header[:20] + pack('<I', flag_bits) + header[24:]
    raw += pack('<H', len(payload)) + payload + b'\x00\x00\x00\x00'
    monkeypatch.setattr(read_write, 'DEFAULT_CHARSET', 'ascii')
    parsed = Lnk.from_bytes(raw)
    assert isinstance(getattr(parsed, field), bytes)
    assert getattr(parsed, field) == payload

    monkeypatch.setattr(read_write, 'DEFAULT_CHARSET', 'cp1252')
    result = json.loads(json.dumps(parsed.json()))
    assert result[field] == 'caf\xe9'
    assert result['link_flags'][flag] is True
    assert result['link_flags']['IsUnicode'] is False
    assert isinstance(getattr(parsed, field), bytes)
    assert getattr(parsed, field) == payload
    assert parsed.link_flags.bytes == flag_bits

    monkeypatch.setattr(read_write, 'DEFAULT_CHARSET', 'utf-8')
    with pytest.raises(UnicodeDecodeError):
        parsed.json()
    assert getattr(parsed, field) == payload
    assert parsed.link_flags.bytes == flag_bits


@pytest.mark.parametrize('description', [
    pytest.param('hello', id='ascii'),
    pytest.param('Привет', id='bmp'),
    pytest.param('a\U0001f600b', id='one-non-bmp'),
    pytest.param('\U0001f600\U0001f642', id='two-non-bmp'),
])
def test_json_parsed_unicode_description(description: str) -> None:
    """UTF-16 code-unit counts preserve text, including surrogate pairs, through parsing."""
    lnk = Lnk()
    lnk.link_flags.IsUnicode = True
    lnk.description = description
    parsed = Lnk.from_bytes(lnk.bytes())
    result = json.loads(json.dumps(parsed.json()))
    assert result['description'] == description
    assert result['link_flags']['HasName'] is True
    assert result['link_flags']['IsUnicode'] is True
