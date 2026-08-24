from datetime import datetime, timedelta, timezone

from app.normalize.dates import parse_feed_datetime


def test_parse_relative_days():
    now = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    assert parse_feed_datetime("2d", now=now) == now - timedelta(days=2)


def test_parse_iso_string():
    parsed = parse_feed_datetime("2025-09-22T14:48:49+00:00")
    assert parsed == datetime(2025, 9, 22, 14, 48, 49, tzinfo=timezone.utc)


def test_parse_unix_seconds():
    parsed = parse_feed_datetime(1700000000)
    assert parsed == datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)


def test_parse_relative_months_not_now():
    now = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    assert parse_feed_datetime("34mo", now=now) == now - timedelta(days=30 * 34)
    assert parse_feed_datetime("1yr", now=now) == now - timedelta(days=365)
