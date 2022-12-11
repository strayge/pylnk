import os

import pytest


@pytest.fixture()
def examples_path() -> str:
    return os.path.join('tests', 'examples')


@pytest.fixture()
def temp_filename() -> str:
    return 'temp.lnk'
