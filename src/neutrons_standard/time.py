"""Time utility module."""

import time

import numpy as np


def timestamp(ensure_unique: bool = False) -> float:
    """Generate a timestamp in seconds."""
    # no args in astimezone() means local timezone
    next_timestamp = time.time_ns() / 1e9  # convert to seconds
    if ensure_unique:
        _previous_timestamp = getattr(timestamp, "_previous_timestamp", None)
        if _previous_timestamp is not None:
            # compare as `time.struct_time` to ensure uniqueness after formatting
            if next_timestamp < _previous_timestamp or time.gmtime(next_timestamp) == time.gmtime(_previous_timestamp):
                next_timestamp = _previous_timestamp + 1.0
        timestamp._previous_timestamp = next_timestamp
    return next_timestamp


def parse_timestamp(ts: float | str | int) -> float:
    """Parse timestamp from expected formats."""
    if isinstance(ts, str):
        # Convert ISO format string to timestamp
        return np.datetime64(ts).astype(int) / 1e9  # convert to seconds
    if isinstance(ts, int):
        # DEPRECIATED: support legacy integer encoding
        return float(ts) / 1000.0
    if not isinstance(ts, float):
        raise ValueError("Timestamp must be a float, int, or ISO format string")
    return float(ts)


def iso_from_timestamp(ts: float) -> str:
    """Convert float timestamp (seconds) to integer nanoseconds."""
    ts_ns = int(ts * 1e9)
    np_datetime = np.datetime64(ts_ns, "ns")
    iso = np.datetime_as_string(np_datetime, timezone="local", unit="ns")
    return iso
