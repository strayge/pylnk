import os

import pytest


@pytest.fixture()
def examples_path():
    return os.path.join('tests', 'examples')


@pytest.fixture()
def temp_filename():
    return 'temp.lnk'
