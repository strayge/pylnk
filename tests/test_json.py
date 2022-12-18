import json
import os
from glob import glob

from pylnk3 import Lnk


def test_parse_as_json(examples_path: str, temp_filename: str) -> None:
    """Test all examples json serialazable."""
    filenames = glob(os.path.join(examples_path, '*.lnk'))
    for filename in filenames:
        lnk = Lnk.from_file(filename)
        json_obj = lnk.json()
        assert 'shell_item_id_list' in json_obj
        assert json.dumps(json_obj)
