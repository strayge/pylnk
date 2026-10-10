from io import BytesIO
from pathlib import Path

import pytest

from pylnk3 import Lnk
from pylnk3.exceptions import FormatException
from pylnk3.structures.id_list.path import PathSegmentFileOrFolderEntry


@pytest.mark.parametrize('as_stream', [False, True], ids=['filename', 'stream'])
def test_rejected_opaque_edit_preserves_destination(
    examples_path: str, temp_filename: str, as_stream: bool,
) -> None:
    """Serialization rejection must not truncate an existing shortcut or partially write a caller's stream."""
    original = (Path(examples_path) / 'local_invalid_beef0004.lnk').read_bytes()
    filename = Path(temp_filename)
    filename.write_bytes(original)
    lnk = Lnk.from_file(temp_filename)
    entry = lnk.shell_item_id_list.items[-1]
    assert isinstance(entry, PathSegmentFileOrFolderEntry)
    entry.full_name = 'changed.exe'
    destination = BytesIO(original) if as_stream else temp_filename
    if isinstance(destination, BytesIO):
        destination.seek(5)
    with pytest.raises(FormatException, match='opaque'):
        lnk.save(destination)
    assert filename.read_bytes() == original
    if isinstance(destination, BytesIO):
        assert destination.getvalue() == original
        assert destination.tell() == 5
        assert not destination.closed


def test_save_to_caller_stream() -> None:
    """Saving buffered data must leave ownership and positioning of a supplied stream with the caller."""
    lnk = Lnk()
    stream = BytesIO(b'prefix')
    stream.seek(6)
    lnk.save(stream)
    assert not stream.closed
    assert stream.getvalue() == b'prefix' + lnk.bytes()
    assert stream.tell() == len(stream.getvalue())


def test_save_forced_extension(tmp_path: Path) -> None:
    """Preflight serialization must retain the existing filename-extension behavior."""
    lnk = Lnk()
    lnk.save(str(tmp_path / 'shortcut'), force_ext=True)
    assert (tmp_path / 'shortcut.lnk').read_bytes() == lnk.bytes()
