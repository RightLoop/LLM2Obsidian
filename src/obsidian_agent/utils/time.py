"""Time helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current UTC time."""

    return datetime.now(timezone.utc)


def compact_timestamp() -> str:
    """Return a compact timestamp for filenames."""

    return now_utc().strftime("%Y%m%d-%H%M%S")
