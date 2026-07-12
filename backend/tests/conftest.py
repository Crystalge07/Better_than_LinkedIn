"""Load real cross-feed dedupe fixtures."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.normalize.adapters.listings_json import map_listing_item
from app.schemas.job import Job

FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "dedupe_pairs.json"
FIXTURE_NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)


def load_fixture_groups() -> dict:
    return json.loads(FIXTURES_PATH.read_text())["groups"]


def jobs_from_fixture_group(group_name: str) -> list[Job]:
    group = load_fixture_groups()[group_name]
    jobs: list[Job] = []
    for entry in group["listings"]:
        job = map_listing_item(
            entry["raw"],
            feed_tag=entry["feed_tag"],
            seen_at=FIXTURE_NOW,
        )
        if job is None:
            raise ValueError(f"Invalid fixture entry in {group_name}")
        jobs.append(job)
    return jobs


def expected_merged_count(group_name: str) -> int:
    return load_fixture_groups()[group_name]["expect_merged_count"]
