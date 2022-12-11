import re
from typing import Union

from pylnk3.exceptions import FormatException
from pylnk3.structures import IDListEntry

_DRIVE_PATTERN = re.compile(r'(\w)[:/\\]*$')


class DriveEntry(IDListEntry):

    def __init__(self, drive: Union[bytes, str]) -> None:
        if len(drive) == 23:
            assert isinstance(drive, bytes)
            # binary data from parsed lnk
            self.drive = drive[1:3]
        else:
            # text representation
            assert isinstance(drive, str)
            m = _DRIVE_PATTERN.match(drive.strip())
            if m:
                drive = m.groups()[0].upper() + ':'
                self.drive = drive.encode()
            else:
                raise FormatException("This is not a valid drive: " + str(drive))

    @property
    def bytes(self) -> bytes:
        drive = self.drive
        padded_str = drive + b'\\' + b'\x00' * 19
        return b'\x2F' + padded_str
        # drive = self.drive
        # if isinstance(drive, str):
        #     drive = drive.encode()
        # return b'/' + drive + b'\\' + b'\x00' * 19

    def __str__(self) -> str:
        return f"<DriveEntry: {self.drive!r}>"
