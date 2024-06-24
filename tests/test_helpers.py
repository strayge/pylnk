from pylnk3 import Lnk, for_file


def test_helpers_for_file(temp_filename: str) -> None:
    path = 'C:\\folder\\file.txt'
    lnk = for_file(path)
    assert lnk.path == path
    lnk.save(temp_filename)
    lnk2 = Lnk.from_file(temp_filename)
    assert lnk2.path == path
