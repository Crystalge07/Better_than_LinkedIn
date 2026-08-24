"""Parse ATS date fields into timezone-aware datetimes."""

import re
from datetime import datetime, timedelta, timezone

_DAYS_AGO = re.compile(r"(\d+)\+?\s+days?\s+ago", re.IGNORECASE)
_MONTHS_AGO = re.compile(r"(\d+)\+?\s+months?\s+ago", re.IGNORECASE)


def parse_iso_datetime(value: object, *, fallback: datetime) -> datetime:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        seconds = value / 1000.0 if value > 10_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return fallback
    text = str(value).strip()
    if not text:
        return fallback
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_workday_posted_on(text: str | None, *, now: datetime) -> datetime:
    """Approximate Workday list labels like 'Posted 4 Days Ago'."""
    if not text:
        return now
    label = text.strip()
    if label.lower().startswith("posted "):
        label = label[7:].strip()
    lowered = label.lower()
    if lowered == "today":
        return now
    if lowered == "yesterday":
        return now - timedelta(days=1)
    days = _DAYS_AGO.search(label)
    if days:
        return now - timedelta(days=int(days.group(1)))
    months = _MONTHS_AGO.search(label)
    if months:
        return now - timedelta(days=30 * int(months.group(1)))
    return parse_iso_datetime(text, fallback=now)
