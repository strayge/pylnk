import os

from pylnk3 import Lnk
from pylnk3.structures.id_list.root import ROOT_UWP_APPS


def get_sub_blocks(lnk: Lnk) -> dict:
    uwp_segment = lnk.shell_item_id_list.items[1]
    sub_blocks = {}
    for main_block in uwp_segment._blocks:
        for sub_block in main_block._blocks:
            if sub_block.name in sub_blocks:
                continue
            sub_blocks[sub_block.name] = sub_block.value
    return sub_blocks


def test_uwp_read(examples_path: str) -> None:
    full_filename = os.path.join(examples_path, 'uwp_calc.lnk')

    lnk = Lnk(full_filename)
    uwp_root = lnk.shell_item_id_list.items[0]
    assert uwp_root.root == ROOT_UWP_APPS

    sub_blocks = get_sub_blocks(lnk)
    assert sub_blocks['PackageFamilyName'] == 'Microsoft.WindowsCalculator_8wekyb3d8bbwe'
    assert sub_blocks['PackageFullName'] == 'Microsoft.WindowsCalculator_10.2008.2.0_x64__8wekyb3d8bbwe'
    assert sub_blocks['Target'] == 'Microsoft.WindowsCalculator_8wekyb3d8bbwe!App'
    assert sub_blocks['Location'] == 'C:\\Program Files\\WindowsApps\\Microsoft.WindowsCalculator_10.2008.2.0_x64__8wekyb3d8bbwe'
    assert sub_blocks['DisplayName'] == 'Calculator'


def test_uwp_write(examples_path: str, temp_filename: str) -> None:
    full_filename = os.path.join(examples_path, 'uwp_calc.lnk')

    lnk = Lnk(full_filename)
    lnk.save(temp_filename)
    lnk2 = Lnk(temp_filename)

    uwp_root = lnk2.shell_item_id_list.items[0]
    assert uwp_root.root == ROOT_UWP_APPS

    sub_blocks = get_sub_blocks(lnk2)
    assert sub_blocks['PackageFamilyName'] == 'Microsoft.WindowsCalculator_8wekyb3d8bbwe'
    assert sub_blocks['PackageFullName'] == 'Microsoft.WindowsCalculator_10.2008.2.0_x64__8wekyb3d8bbwe'
    assert sub_blocks['Target'] == 'Microsoft.WindowsCalculator_8wekyb3d8bbwe!App'
    assert sub_blocks['Location'] == 'C:\\Program Files\\WindowsApps\\Microsoft.WindowsCalculator_10.2008.2.0_x64__8wekyb3d8bbwe'
    assert sub_blocks['DisplayName'] == 'Calculator'
