from typing import Union

from pylnk3.structures.id_list.base import IDListEntry
from pylnk3.utils.guid import guid_from_bytes

ROOT_MY_COMPUTER = 'MY_COMPUTER'
ROOT_NETWORK_PLACES = 'NETWORK_PLACES'
ROOT_MY_DOCUMENTS = 'MY_DOCUMENTS'
ROOT_NETWORK_SHARE = 'NETWORK_SHARE'
ROOT_NETWORK_SERVER = 'NETWORK_SERVER'
ROOT_NETWORK_DOMAIN = 'NETWORK_DOMAIN'
ROOT_INTERNET = 'INTERNET'
RECYCLE_BIN = 'RECYCLE_BIN'
ROOT_CONTROL_PANEL = 'CONTROL_PANEL'
ROOT_USER = 'USERPROFILE'
ROOT_UWP_APPS = 'APPS'

_ROOT_LOCATIONS = {
    '{20D04FE0-3AEA-1069-A2D8-08002B30309D}': ROOT_MY_COMPUTER,
    '{450D8FBA-AD25-11D0-98A8-0800361B1103}': ROOT_MY_DOCUMENTS,
    '{54a754c0-4bf1-11d1-83ee-00a0c90dc849}': ROOT_NETWORK_SHARE,
    '{c0542a90-4bf0-11d1-83ee-00a0c90dc849}': ROOT_NETWORK_SERVER,
    '{208D2C60-3AEA-1069-A2D7-08002B30309D}': ROOT_NETWORK_PLACES,
    '{46e06680-4bf0-11d1-83ee-00a0c90dc849}': ROOT_NETWORK_DOMAIN,
    '{871C5380-42A0-1069-A2EA-08002B30309D}': ROOT_INTERNET,
    '{645FF040-5081-101B-9F08-00AA002F954E}': RECYCLE_BIN,
    '{21EC2020-3AEA-1069-A2DD-08002B30309D}': ROOT_CONTROL_PANEL,
    '{59031A47-3F72-44A7-89C5-5595FE6B30EE}': ROOT_USER,
    '{4234D49B-0245-4DF3-B780-3893943456E1}': ROOT_UWP_APPS,
}
_ROOT_LOCATION_GUIDS = dict((v, k) for k, v in _ROOT_LOCATIONS.items())


class RootEntry(IDListEntry):

    def __init__(self, root: Union[str, bytes]) -> None:
        if root is not None:
            # create from text representation
            if isinstance(root, str):
                self.root = root
                self.guid: str = _ROOT_LOCATION_GUIDS[root]
                return
            else:
                # from binary
                root_type = root[0]
                index = root[1]
                guid_bytes = root[2:18]
                self.guid = guid_from_bytes(guid_bytes)
                self.root = _ROOT_LOCATIONS.get(self.guid, f"UNKNOWN {self.guid}")
                # if self.root == "UNKNOWN":
                #     self.root = _ROOT_INDEX.get(index, "UNKNOWN")

    @property
    def bytes(self) -> bytes:
        guid = self.guid[1:-1].replace('-', '')
        chars = [bytes([int(x, 16)]) for x in [guid[i:i + 2] for i in range(0, 32, 2)]]
        return (
            b'\x1F\x50'
            + chars[3] + chars[2] + chars[1] + chars[0]
            + chars[5] + chars[4] + chars[7] + chars[6]
            + b''.join(chars[8:])
        )

    def __str__(self) -> str:
        return "<RootEntry: %s>" % self.root
