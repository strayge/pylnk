import json
import os
import time
from datetime import datetime, tzinfo
from struct import pack, unpack_from
from typing import Optional

import pytest

from pylnk3 import Lnk
from pylnk3.structures.extra_data import TypedPropertyValue
from pylnk3.utils import data
from pylnk3.utils.data import convert_time_to_unix, convert_time_to_windows


def test_unset_filetime_and_numeric_epoch() -> None:
    """Unset FILETIMEs and numeric Unix zero are distinct inputs."""
    assert convert_time_to_unix(0) is None
    assert convert_time_to_windows(None) == 0
    assert convert_time_to_windows(0) == 116444736000000000
    assert convert_time_to_unix(116444736000000000) == datetime.fromtimestamp(0)
    assert convert_time_to_windows(1.25) == 116444736012500000


@pytest.mark.parametrize(('microseconds', 'last_digit'), [(0, 0), (123456, 7), (999999, 9)])
def test_filetime_integer_precision(microseconds: int, last_digit: int) -> None:
    """Epoch arithmetic independently checks precision and sub-microsecond truncation."""
    utc_time = datetime(2024, 1, 15, 12, 30, 40, microseconds)
    since_filetime_epoch = utc_time - datetime(1601, 1, 1)
    ticks = (
        (since_filetime_epoch.days * 86400 + since_filetime_epoch.seconds) * 10000000
        + microseconds * 10 + last_digit
    )
    since_unix_epoch = utc_time - datetime(1970, 1, 1)
    seconds = since_unix_epoch.days * 86400 + since_unix_epoch.seconds
    expected = datetime.fromtimestamp(seconds).replace(microsecond=microseconds)
    decoded = convert_time_to_unix(ticks)
    assert decoded == expected
    assert decoded is not None
    assert decoded.tzinfo is None
    assert convert_time_to_windows(decoded) == ticks - last_digit


def test_unset_header_json_and_bytes() -> None:
    """Explicit unset header fields stay zero on disk and null in JSON."""
    lnk = Lnk()
    assert all(isinstance(getattr(lnk, field), datetime) for field in (
        'creation_time', 'access_time', 'modification_time',
    ))
    lnk.creation_time = lnk.access_time = lnk.modification_time = None
    raw = lnk.bytes()
    assert unpack_from('<3Q', raw, 0x1C) == (0, 0, 0)
    restored = Lnk.from_bytes(raw)
    result = json.loads(json.dumps(restored.json()))
    for field in ('creation_time', 'access_time', 'modification_time'):
        assert getattr(restored, field) is None
        assert result[field] is None
    assert unpack_from('<3Q', restored.bytes(), 0x1C) == (0, 0, 0)


@pytest.mark.parametrize('ticks', [0, 116444736001234567])
def test_property_filetime_preserves_raw_bytes(ticks: int) -> None:
    """JSON decoding must not rewrite opaque property bytes, even when ticks are unset."""
    raw = pack('<HHQ', 0x40, 0, ticks)
    prop = TypedPropertyValue(raw)
    expected = None if ticks == 0 else datetime.fromtimestamp(0).replace(microsecond=123456).isoformat()
    assert prop.value_decoded == expected
    result = json.loads(json.dumps(prop.json()))
    assert result['value_decoded'] == expected
    assert result['value'] == raw[4:].hex()
    assert prop.value == raw[4:]
    assert prop.bytes == raw


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='Local timezone control requires tzset.')
def test_local_dst_fold_roundtrip() -> None:
    """The repeated local hour must retain its distinct instants without a timezone database."""
    previous_tz = os.environ.get('TZ')
    try:
        os.environ['TZ'] = 'EST5EDT,M3.2.0/2,M11.1.0/2'
        time.tzset()
        for fold, utc_hour in ((0, 5), (1, 6)):
            since_epoch = datetime(2024, 11, 3, utc_hour, 30) - datetime(1601, 1, 1)
            ticks = (since_epoch.days * 86400 + since_epoch.seconds) * 10000000 + 1234560
            expected = datetime(2024, 11, 3, 1, 30, microsecond=123456, fold=fold)
            decoded = convert_time_to_unix(ticks)
            assert decoded == expected
            assert decoded is not None
            assert decoded.tzinfo is None
            assert decoded.fold == fold
            assert convert_time_to_windows(expected) == ticks
            assert convert_time_to_windows(decoded) == ticks
    finally:
        if previous_tz is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = previous_tz
        time.tzset()


def test_conversion_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Platform conversion failures must not fabricate a timestamp from the current clock."""
    class UnsupportedDatetime(datetime):
        """Simulate unavailable platform conversions without depending on its date range."""

        @classmethod
        def fromtimestamp(cls, timestamp: float, tz: Optional[tzinfo] = None) -> 'UnsupportedDatetime':
            raise OSError('unsupported read time')

        def timestamp(self) -> float:
            raise OverflowError('unsupported write time')

    monkeypatch.setattr(data, 'datetime', UnsupportedDatetime)
    assert convert_time_to_unix(0) is None
    assert convert_time_to_windows(None) == 0
    with pytest.raises(OSError, match='unsupported read time'):
        convert_time_to_unix(116444736000000000)
    with pytest.raises(OverflowError, match='unsupported write time'):
        convert_time_to_windows(UnsupportedDatetime(2024, 1, 15))
