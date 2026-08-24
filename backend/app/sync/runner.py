"""Orchestrate feed fetch, company-board fetch, normalize, and DB sync."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ats.company_date import overlay_company_posted_dates
from app.ats.direct_apply import resolve_company_apply_urls
from app.ats.runner import fetch_company_jobs
from app.fetch.client import HttpFetcher, fetch_json, fetch_text
from app.normalize.adapters.base import FeedAdapter
from app.normalize.adapters.heynish_dach import HeynishDachAdapter
from app.normalize.adapters.simplify_internships import (
    FEED_TAG_2027 as SIMPLIFY_INTERNSHIPS_2027,
    FEED_URL_2027 as SIMPLIFY_INTERNSHIPS_2027_URL,
    SimplifyInternshipsAdapter,
)
from app.normalize.adapters.simplify_new_grad import SimplifyNewGradAdapter
from app.normalize.adapters.speedyapply import (
    AI_MARKDOWN_URLS,
    SWE_MARKDOWN_URLS,
    SpeedyApplyAdapter,
)
from app.normalize.adapters.vanshb03_new_grad import (
    FEED_TAG_2027 as VANSHB03_2027,
    FEED_URL_2027 as VANSHB03_2027_URL,
    Vanshb03NewGradAdapter,
)
from app.normalize.adapters.warpjobs import WarpJobsAdapter
from app.normalize.dedupe import merge_jobs
from app.schemas.job import Job
from app.store.repository import sync_jobs

logger = logging.getLogger(__name__)

FEED_ADAPTERS: list[FeedAdapter] = [
    SimplifyInternshipsAdapter(),
    SimplifyInternshipsAdapter(SIMPLIFY_INTERNSHIPS_2027, SIMPLIFY_INTERNSHIPS_2027_URL),
    SimplifyNewGradAdapter(),
    Vanshb03NewGradAdapter(),
    Vanshb03NewGradAdapter(VANSHB03_2027, VANSHB03_2027_URL),
    SpeedyApplyAdapter("speedyapply_swe_2027", SWE_MARKDOWN_URLS),
    SpeedyApplyAdapter("speedyapply_ai_2027", AI_MARKDOWN_URLS),
    WarpJobsAdapter(),
    HeynishDachAdapter(),
]


@dataclass(frozen=True)
class SyncRunStats:
    inserted: int
    updated: int
    deactivated: int
    feeds_ok: int
    feeds_failed: int
    boards_ok: int
    boards_failed: int
    jobs_fetched: int


def run_sync(session: Session) -> SyncRunStats:
    """Fetch GitHub feeds plus company boards and apply diff/upsert to Postgres."""
    synced_at = datetime.now(timezone.utc)
    fetched_jobs: list[Job] = []
    successful_sources: set[str] = set()
    feeds_ok = 0
    feeds_failed = 0

    for adapter in FEED_ADAPTERS:
        try:
            jobs = adapter.fetch_and_normalize(fetch_json, fetch_text=fetch_text)
        except Exception:
            logger.exception("Feed failed: %s (%s)", adapter.source_name, adapter.feed_url)
            feeds_failed += 1
            continue

        feeds_ok += 1
        successful_sources.add(adapter.source_name)
        fetched_jobs.extend(jobs)
        logger.info("Normalized %d jobs from %s", len(jobs), adapter.source_name)

    with HttpFetcher() as http:
        board_jobs, board_sources, boards_ok, boards_failed = fetch_company_jobs(
            http.fetch_json, http.post_json
        )
        fetched_jobs.extend(board_jobs)
        fetched_jobs = resolve_company_apply_urls(
            fetched_jobs, fetch_text=http.fetch_text
        )
        fetched_jobs = overlay_company_posted_dates(
            fetched_jobs, fetch_json=http.fetch_json
        )
    successful_sources.update(board_sources)
    logger.info(
        "Company boards: jobs=%d ok=%d failed=%d",
        len(board_jobs),
        boards_ok,
        boards_failed,
    )

    deduped_jobs = merge_jobs(fetched_jobs)
    if len(deduped_jobs) != len(fetched_jobs):
        logger.info(
            "Deduped %d fetched jobs to %d unique postings",
            len(fetched_jobs),
            len(deduped_jobs),
        )

    inserted, updated, deactivated = sync_jobs(
        session,
        deduped_jobs,
        successful_sources=successful_sources,
        synced_at=synced_at,
    )

    stats = SyncRunStats(
        inserted=inserted,
        updated=updated,
        deactivated=deactivated,
        feeds_ok=feeds_ok,
        feeds_failed=feeds_failed,
        boards_ok=boards_ok,
        boards_failed=boards_failed,
        jobs_fetched=len(fetched_jobs),
    )
    logger.info(
        "Sync complete: fetched=%d inserted=%d updated=%d deactivated=%d "
        "feeds_ok=%d feeds_failed=%d boards_ok=%d boards_failed=%d",
        stats.jobs_fetched,
        stats.inserted,
        stats.updated,
        stats.deactivated,
        stats.feeds_ok,
        stats.feeds_failed,
        stats.boards_ok,
        stats.boards_failed,
    )
    return stats
