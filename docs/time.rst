=======================
Time Utilities (time)
=======================

High-precision timestamp generation, parsing, and ISO 8601 formatting with nanosecond accuracy.

Quick Reference
===============

.. code-block:: python

    from neutrons_standard.time import timestamp, parse_timestamp, iso_from_timestamp

    # Generate timestamps
    ts = timestamp()                              # Current time (float seconds)
    ts = timestamp(ensure_unique=True)            # Unique, monotonically increasing

    # Convert between formats
    float_seconds = parse_timestamp("2026-03-04T16:10:34.817Z")    # ISO string → float
    float_seconds = parse_timestamp(1741100434.817)                # Float → float
    float_seconds = parse_timestamp(1741100434817)                 # Milliseconds → float

    # Format for display/storage
    iso_str = iso_from_timestamp(1741100434.817)  # 2026-03-04T16:10:34.817000000Z

timestamp()
-----------

Generate current timestamp in seconds (float) with nanosecond precision:

.. code-block:: python

    ts = timestamp()                    # 1741100434.817123456
    ts = timestamp(ensure_unique=True)  # Guaranteed > previous, even in same second

**Parameters:**

- ``ensure_unique`` (bool): If True, timestamps are monotonically increasing (useful for event ordering)

**Returns:** float (seconds since epoch)

parse_timestamp()
-----------------

Parse timestamps from multiple formats to float seconds:

.. code-block:: python

    parse_timestamp("2026-03-04T16:10:34.817Z")  # ISO 8601 string
    parse_timestamp(1741100434.817)               # Float seconds
    parse_timestamp(1741100434817)                # Legacy milliseconds (int)

**Parameters:**

- ``ts`` (str | float | int): Timestamp in supported format

**Returns:** float (seconds since epoch)

**Formats:**

- ISO 8601 string: ``"2026-03-04T16:10:34.817Z"``
- Float seconds: ``1741100434.817``
- Integer milliseconds: ``1741100434817`` (deprecated)

iso_from_timestamp()
--------------------

Convert float seconds to ISO 8601 string with nanosecond precision and timezone:

.. code-block:: python

    iso = iso_from_timestamp(1741100434.817)
    # Returns: "2026-03-04T16:10:34.817000000Z"

**Parameters:**

- ``ts`` (float): Seconds since epoch

**Returns:** str (ISO 8601 format with nanosecond precision and local timezone)

Examples
========

Event Logging
-------------

.. code-block:: python

    from neutrons_standard.time import timestamp, iso_from_timestamp

    events = []
    for event_type in ["login", "query", "logout"]:
        events.append({
            'type': event_type,
            'timestamp': iso_from_timestamp(timestamp(ensure_unique=True))
        })
    # Guaranteed ordering: each timestamp strictly increases

Performance Measurement
-----------------------

.. code-block:: python

    from neutrons_standard.time import timestamp

    start = timestamp()
    perform_operation()
    elapsed = timestamp() - start
    print(f"Operation took {elapsed} seconds")

Timestamp Conversion Round-Trip
-------------------------------

.. code-block:: python

    from neutrons_standard.time import timestamp, iso_from_timestamp, parse_timestamp

    # Original timestamp
    ts1 = timestamp()

    # Convert to ISO and back
    iso = iso_from_timestamp(ts1)            # "2026-03-04T16:10:34.817Z"
    ts2 = parse_timestamp(iso)

    # Minor rounding error, but functionally equivalent
    assert abs(ts1 - ts2) < 0.001

Configuration Backup Timestamping
----------------------------------

.. code-block:: python

    from neutrons_standard.time import iso_from_timestamp, timestamp
    from pathlib import Path

    def backup_file(filepath):
        backup_time = iso_from_timestamp(timestamp())
        backup_path = Path(filepath).parent / f"{filepath}-{backup_time}.bak"
        shutil.copy(filepath, backup_path)
        return backup_path

Use Cases
=========

Audit Trails
------------

.. code-block:: python

    from neutrons_standard.time import timestamp, iso_from_timestamp

    class AuditLog:
        def __init__(self):
            self.events = []

        def record(self, action, details):
            self.events.append({
                'action': action,
                'timestamp': iso_from_timestamp(timestamp(ensure_unique=True)),
                'details': details
            })

    audit = AuditLog()
    audit.record("user_login", {"user": "alice"})
    audit.record("data_export", {"table": "sales"})

Time Series Data
----------------

.. code-block:: python

    from neutrons_standard.time import timestamp, iso_from_timestamp

    class TimeSeries:
        def __init__(self):
            self.points = []

        def add_point(self, value):
            self.points.append({
                'timestamp': timestamp(ensure_unique=True),
                'value': value
            })

        def export_csv(self):
            lines = ["timestamp,value"]
            for point in self.points:
                iso_ts = iso_from_timestamp(point['timestamp'])
                lines.append(f"{iso_ts},{point['value']}")
            return "\n".join(lines)

Database Integration
--------------------

.. code-block:: python

    from neutrons_standard.time import timestamp, iso_from_timestamp, parse_timestamp

    class DatabaseRecord:
        def __init__(self, data):
            self.data = data
            self.created_at = timestamp()

        def to_db(self):
            """Save to database with ISO timestamp."""
            return {
                **self.data,
                'created_at': iso_from_timestamp(self.created_at)
            }

        @classmethod
        def from_db(cls, db_row):
            """Load from database."""
            record = cls(db_row)
            record.created_at = parse_timestamp(db_row['created_at'])
            return record

Precision and Guarantees
========================

Nanosecond Precision
--------------------

All timestamps maintain nanosecond precision (9 decimal places):

.. code-block:: python

    iso = iso_from_timestamp(timestamp())
    # "2026-03-04T16:10:34.817123456Z"  <- 9 decimal places (nanoseconds)

Monotonic Uniqueness
--------------------

With ``ensure_unique=True``, timestamps strictly increase even in same second:

.. code-block:: python

    from neutrons_standard.time import timestamp

    times = [timestamp(ensure_unique=True) for _ in range(100)]

    # Each is strictly greater than the previous
    for i in range(len(times) - 1):
        assert times[i] < times[i + 1]

Format Examples
===============

.. code-block:: text

    Float seconds:
      1741100434.817123456

    ISO 8601 (with nanoseconds):
      2026-03-04T16:10:34.817123456Z
      │         │ │  │  │  │          │
      Year ─────┘ │  │  │  │          │
      Month ──────┘  │  │  │          │
      Day ───────────┘  │  │          │
      Hour ────────────┘  │          │
      Minute ─────────────┘          │
      Second & nanoseconds ──────────┘
      Timezone indicator: Z = UTC

    Milliseconds (legacy):
      1741100434817
