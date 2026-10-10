from pathlib import Path

import pytest


@pytest.fixture()
def examples_path() -> str:
    return str(Path(__file__).parent / 'data')


@pytest.fixture()
def temp_filename(tmp_path: Path) -> str:
    return str(tmp_path / 'shortcut.lnk')
