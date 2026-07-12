"""Shared mapping for Simplify/vanshb03-style listings.json feeds."""

from datetime import datetime, timezone

from app.normalize.fingerprint import compute_fingerprint
from app.schemas.job import Job


def parse_unix_timestamp(value: object) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return datetime.now(timezone.utc)


def map_listing_item(item: dict, *, feed_tag: str, seen_at: datetime) -> Job | None:
    """Map one raw listings.json object into a Job, or None if invalid."""
    company = (item.get("company_name") or "").strip()
    title = (item.get("title") or "").strip()
    apply_url = (item.get("url") or "").strip()
    source_job_id = (item.get("id") or "").strip()

    if not company or not title or not apply_url or not source_job_id:
        return None

    locations = [loc.strip() for loc in item.get("locations") or [] if loc]
    if not locations:
        locations = ["Unknown"]

    date_posted = parse_unix_timestamp(item.get("date_posted"))
    fingerprint = compute_fingerprint(company, title, locations)

    return Job(
        company=company,
        title=title,
        locations=locations,
        apply_url=apply_url,
        date_posted=date_posted,
        source=feed_tag,
        source_job_id=source_job_id,
        sources=[feed_tag],
        first_seen=seen_at,
        last_seen=seen_at,
        active=True,
        posting_active=bool(item.get("active", True)),
        fingerprint=fingerprint,
    )
