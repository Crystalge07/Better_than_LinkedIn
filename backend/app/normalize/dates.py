"""Parse messy feed timestamps into timezone-aware datetimes."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# Months before `m` so `1mo` is not read as 1 minute.
_RELATIVE_AGE = re.compile(
    r"^\s*(\d+)\s*(years?|yrs?|y|months?|mos?|weeks?|wks?|w|days?|d|hours?|h|minutes?|mins?|m)\s*$",
    re.IGNORECASE,
)


def parse_feed_datetime(value: object, *, now: datetime | None = None) -> datetime:
    """Best-effort parse of unix seconds, ISO strings, or relative ages like `2d`."""
    now = now or datetime.now(timezone.utc)

    if value is None or value == "":
        return now
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _from_unix(value, now)

    text = str(value).strip()
    if not text:
        return now

    relative = _RELATIVE_AGE.match(text)
    if relative:
        return now - _relative_delta(int(relative.group(1)), relative.group(2).lower())

    if text.isdigit():
        return _from_unix(int(text), now)

    iso = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        return now
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _relative_delta(amount: int, unit: str) -> timedelta:
    if unit in {"year", "years", "yr", "yrs", "y"}:
        return timedelta(days=365 * amount)
    if unit in {"month", "months", "mo", "mos"}:
        return timedelta(days=30 * amount)
    if unit in {"week", "weeks", "wk", "wks", "w"}:
        return timedelta(weeks=amount)
    if unit in {"day", "days", "d"}:
        return timedelta(days=amount)
    if unit in {"hour", "hours", "h"}:
        return timedelta(hours=amount)
    return timedelta(minutes=amount)


def _from_unix(value: int | float, fallback: datetime) -> datetime:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return fallback
