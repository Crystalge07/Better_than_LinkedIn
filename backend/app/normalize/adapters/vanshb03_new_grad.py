"""Adapter for vanshb03 New-Grad-2026 feed."""

from datetime import datetime, timezone

from app.normalize.adapters.base import FeedAdapter
from app.normalize.adapters.listings_json import map_listing_item
from app.schemas.job import Job

FEED_URL = (
    "https://raw.githubusercontent.com/vanshb03/New-Grad-2026/dev/"
    ".github/scripts/listings.json"
)
FEED_TAG = "vanshb03_new_grad"


class Vanshb03NewGradAdapter(FeedAdapter):
    source_name = FEED_TAG
    feed_url = FEED_URL

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
