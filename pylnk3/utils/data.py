import time
from datetime import datetime
from typing import Union


def convert_time_to_unix(windows_time: int) -> datetime:
    # Windows time is specified as the number of 0.1 nanoseconds since January 1, 1601.
    # UNIX time is specified as the number of seconds since January 1, 1970.
    # There are 134774 days (or 11644473600 seconds) between these dates.
    unix_time = windows_time / 10000000.0 - 11644473600
    try:
        return datetime.fromtimestamp(unix_time)
    except OSError:
        return datetime.now()


def convert_time_to_windows(unix_time: Union[int, datetime]) -> int:
    if isinstance(unix_time, datetime):
        try:
            unix_time_int = time.mktime(unix_time.timetuple())
        except OverflowError:
            unix_time_int = time.mktime(datetime.now().timetuple())
    else:
        unix_time_int = unix_time
    return int((unix_time_int + 11644473600) * 10000000)
