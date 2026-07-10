"""iios/integration/normalization/timestamp_normalizer.py

Normalizes timestamps to UTC epoch floats.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any

from iios.integration.integration_exceptions import TimestampNormalizationError


# ISO 8601 with optional timezone
_ISO_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(\.\d+)?"
    r"(Z|[+-]\d{2}:?\d{2})?$"
)


class TimestampNormalizer:
    """
    Converts heterogeneous timestamp formats to UTC epoch float.

    Supported inputs:
    - float / int (assumed UTC epoch seconds)
    - ISO 8601 strings (with or without timezone)
    - datetime objects (naive treated as local or UTC depending on config)
    - millisecond integers (>= 1e12 treated as ms)
    """

    def __init__(self, naive_as_utc: bool = True) -> None:
        self._naive_as_utc = naive_as_utc

    def normalize(self, value: Any) -> float:
        """Convert *value* to a UTC epoch float (seconds since 1970-01-01 00:00:00 UTC)."""
        if isinstance(value, float):
            return self._handle_numeric(value)
        if isinstance(value, int):
            return self._handle_numeric(float(value))
        if isinstance(value, str):
            return self._handle_string(value)
        if isinstance(value, datetime):
            return self._handle_datetime(value)
        raise TimestampNormalizationError(
            f"Cannot normalize timestamp of type {type(value).__name__}: {value!r}"
        )

    def _handle_numeric(self, value: float) -> float:
        # Milliseconds check: assume ms if > year 3000 in seconds
        if value >= 1e12:
            return value / 1_000.0
        # Microseconds check
        if value >= 1e15:
            return value / 1_000_000.0
        return value

    def _handle_string(self, value: str) -> float:
        value = value.strip()
        # Try numeric string first
        try:
            return self._handle_numeric(float(value))
        except ValueError:
            pass
        # Try ISO 8601
        m = _ISO_RE.match(value)
        if m:
            year, month, day, hour, minute, second = (int(x) for x in m.groups()[:6])
            frac_str = m.group(7) or ""
            microsecond = round(float("0" + frac_str) * 1_000_000) if frac_str else 0
            tz_str = m.group(8) or ""
            if tz_str == "" or tz_str is None:
                tz = timezone.utc if self._naive_as_utc else None
            elif tz_str == "Z":
                tz = timezone.utc
            else:
                tz_str = tz_str.replace(":", "")
                sign = 1 if tz_str[0] == "+" else -1
                hh   = int(tz_str[1:3])
                mm   = int(tz_str[3:5]) if len(tz_str) >= 5 else 0
                tz   = timezone(timedelta(hours=sign * hh, minutes=sign * mm))
            dt = datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tz)
            return dt.timestamp()
        raise TimestampNormalizationError(
            f"Cannot parse timestamp string: {value!r}"
        )

    def _handle_datetime(self, dt: datetime) -> float:
        if dt.tzinfo is None:
            if self._naive_as_utc:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
        return dt.timestamp()
