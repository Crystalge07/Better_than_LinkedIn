"""Orchestrate feed fetch, normalize, and DB sync."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.fetch.client import fetch_json
from app.normalize.adapters.base import FeedAdapter
from app.normalize.adapters.simplify_internships import SimplifyInternshipsAdapter
from app.schemas.job import Job
from app.store.repository import sync_jobs

logger = logging.getLogger(__name__)

FEED_ADAPTERS: list[FeedAdapter] = [
    SimplifyInternshipsAdapter(),
]


@dataclass(frozen=True)
class SyncRunStats:
    inserted: int
    updated: int
    deactivated: int
    feeds_ok: int
    feeds_failed: int
    jobs_fetched: int


def run_sync(session: Session) -> SyncRunStats:
    """Fetch all configured feeds and apply diff/upsert to Postgres."""
    synced_at = datetime.now(timezone.utc)
    fetched_jobs: list[Job] = []
    successful_sources: set[str] = set()
    feeds_ok = 0
    feeds_failed = 0

    for adapter in FEED_ADAPTERS:
        try:
            jobs = adapter.fetch_and_normalize(fetch_json)
        except Exception:
            logger.exception("Feed failed: %s (%s)", adapter.source_name, adapter.feed_url)
            feeds_failed += 1
            continue

        feeds_ok += 1
        successful_sources.add(adapter.source_name)
        fetched_jobs.extend(jobs)
        logger.info("Normalized %d jobs from %s", len(jobs), adapter.source_name)

    inserted, updated, deactivated = sync_jobs(
        session,
        fetched_jobs,
        successful_sources=successful_sources,
        synced_at=synced_at,
    )

    stats = SyncRunStats(
        inserted=inserted,
        updated=updated,
        deactivated=deactivated,
        feeds_ok=feeds_ok,
        feeds_failed=feeds_failed,
        jobs_fetched=len(fetched_jobs),
    )
    logger.info(
        "Sync complete: fetched=%d inserted=%d updated=%d deactivated=%d feeds_ok=%d feeds_failed=%d",
        stats.jobs_fetched,
        stats.inserted,
        stats.updated,
        stats.deactivated,
        stats.feeds_ok,
        stats.feeds_failed,
    )
    return stats
