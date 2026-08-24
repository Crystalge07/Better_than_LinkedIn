"""Shared mapping for Simplify/vanshb03-style listings.json feeds."""

from datetime import datetime, timezone

from app.normalize.adapters.base import FeedAdapter
from app.normalize.dates import parse_feed_datetime
from app.normalize.fingerprint import compute_fingerprint
from app.schemas.job import Job


def parse_unix_timestamp(value: object) -> datetime:
    return parse_feed_datetime(value)


def build_job(
    *,
    company: str,
    title: str,
    locations: list[str],
    apply_url: str,
    date_posted: datetime,
    feed_tag: str,
    source_job_id: str,
    seen_at: datetime,
    posting_active: bool = True,
) -> Job:
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
        posting_active=posting_active,
        fingerprint=fingerprint,
    )


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
    return build_job(
        company=company,
        title=title,
        locations=locations,
        apply_url=apply_url,
        date_posted=date_posted,
        feed_tag=feed_tag,
        source_job_id=source_job_id,
        seen_at=seen_at,
        posting_active=bool(item.get("active", True)),
    )


class ListingsJsonAdapter(FeedAdapter):
    """Parameterized adapter for any Simplify-style listings.json array."""

    def __init__(self, source_name: str, feed_url: str) -> None:
        self.source_name = source_name
        self.feed_url = feed_url

    def normalize(self, raw: list | dict) -> list[Job]:
        if not isinstance(raw, list):
            raise ValueError(f"Expected list from {self.source_name}, got {type(raw).__name__}")

        now = datetime.now(timezone.utc)
        jobs: list[Job] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            job = map_listing_item(item, feed_tag=self.source_name, seen_at=now)
            if job is not None:
                jobs.append(job)
        return jobs
