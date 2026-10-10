from datetime import datetime
from typing import Optional, Union


def convert_time_to_unix(windows_time: int) -> Optional[datetime]:
    if windows_time == 0:
        return None
    # FILETIME counts 100-nanosecond ticks since 1601, 11644473600 seconds before Unix time.
    seconds, ticks = divmod(windows_time, 10000000)
    return datetime.fromtimestamp(seconds - 11644473600).replace(microsecond=ticks // 10)


def convert_time_to_windows(unix_time: Optional[Union[int, float, datetime]]) -> int:
    if unix_time is None:
        return 0
    if isinstance(unix_time, datetime):
        # timestamp() honors fold in repeated local hours; keep the fractional ticks separate.
        seconds = int(unix_time.replace(microsecond=0).timestamp())
        return (seconds + 11644473600) * 10000000 + unix_time.microsecond * 10
    return 11644473600 * 10000000 + int(unix_time * 10000000)
