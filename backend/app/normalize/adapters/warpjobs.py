"""Adapter for warpjobs.com/jobs.json (listed in awesome-job-boards)."""

from datetime import datetime, timezone

from app.normalize.adapters.base import FeedAdapter
from app.normalize.adapters.listings_json import build_job
from app.normalize.dates import parse_feed_datetime
from app.schemas.job import Job

FEED_URL = "https://warpjobs.com/jobs.json"
FEED_TAG = "warpjobs"


def map_warp_job(item: dict, *, feed_tag: str, seen_at: datetime) -> Job | None:
    company = (item.get("company") or "").strip()
    title = (item.get("title") or "").strip()
    apply_url = (item.get("url") or "").strip()
    if not company or not title or not apply_url:
        return None

    locations = [loc.strip() for loc in item.get("locations") or [] if loc]
    if item.get("region") and item["region"] not in locations:
        locations.append(str(item["region"]).strip())
    if not locations:
        locations = ["Unknown"]

    source_job_id = apply_url.rsplit("/", 2)[-2] if "/jobs/" in apply_url else apply_url
    return build_job(
        company=company,
        title=title,
        locations=locations,
        apply_url=apply_url,
        date_posted=parse_feed_datetime(item.get("posted"), now=seen_at),
        feed_tag=feed_tag,
        source_job_id=str(source_job_id)[:120],
        seen_at=seen_at,
        posting_active=True,
    )


class WarpJobsAdapter(FeedAdapter):
    source_name = FEED_TAG
    feed_url = FEED_URL

    def normalize(self, raw: list | dict) -> list[Job]:
        if isinstance(raw, dict):
            items = raw.get("jobs")
        else:
            items = raw
        if not isinstance(items, list):
            raise ValueError(f"Expected jobs list from {self.source_name}")

        now = datetime.now(timezone.utc)
        jobs: list[Job] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            job = map_warp_job(item, feed_tag=self.source_name, seen_at=now)
            if job is not None:
                jobs.append(job)
        return jobs
