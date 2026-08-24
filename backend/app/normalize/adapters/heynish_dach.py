"""Adapter for heynish/werkstudent-praktikum-jobs (nested from awesome-job-boards)."""

from datetime import datetime, timezone

from app.normalize.adapters.base import FeedAdapter
from app.normalize.adapters.listings_json import build_job
from app.normalize.dates import parse_feed_datetime
from app.schemas.job import Job

FEED_URL = (
    "https://raw.githubusercontent.com/heynish/werkstudent-praktikum-jobs/main/jobs.json"
)
FEED_TAG = "heynish_dach"


def map_heynish_role(item: dict, *, feed_tag: str, seen_at: datetime) -> Job | None:
    company = (item.get("company") or "").strip()
    title = (item.get("title") or "").strip()
    apply_url = (item.get("raw_url") or item.get("careerkit_apply_url") or "").strip()
    if not company or not title or not apply_url:
        return None

    location = (item.get("location") or item.get("city") or "").strip() or "Unknown"
    source_job_id = apply_url
    return build_job(
        company=company,
        title=title,
        locations=[location],
        apply_url=apply_url,
        date_posted=parse_feed_datetime(item.get("posted"), now=seen_at),
        feed_tag=feed_tag,
        source_job_id=source_job_id[:120],
        seen_at=seen_at,
        posting_active=True,
    )


class HeynishDachAdapter(FeedAdapter):
    source_name = FEED_TAG
    feed_url = FEED_URL

    def normalize(self, raw: list | dict) -> list[Job]:
        if isinstance(raw, dict):
            items = raw.get("roles")
        else:
            items = raw
        if not isinstance(items, list):
            raise ValueError(f"Expected roles list from {self.source_name}")

        now = datetime.now(timezone.utc)
        jobs: list[Job] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            job = map_heynish_role(item, feed_tag=self.source_name, seen_at=now)
            if job is not None:
                jobs.append(job)
        return jobs
