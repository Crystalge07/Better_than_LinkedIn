"""Persist normalized jobs to Postgres."""

import logging
from datetime import datetime

from sqlalchemy import func, literal, or_
from sqlalchemy.orm import Session

from app.schemas.job import Job, JobRead
from app.store.models import JobRow

logger = logging.getLogger(__name__)

_LIKE_ESCAPE = "\\"


def _contains_pattern(value: str) -> str:
    """Build a LIKE/ILIKE contains pattern. Caller passes this as a bound param value.

    Escapes LIKE metacharacters in user input so they are matched literally.
    """
    escaped = (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE + _LIKE_ESCAPE)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )
    return f"%{escaped}%"


def sync_jobs(
    session: Session,
    jobs: list[Job],
    *,
    successful_sources: set[str],
    synced_at: datetime,
) -> tuple[int, int, int]:
    """Diff/upsert jobs from a sync run. Returns (inserted, updated, deactivated)."""
    inserted = 0
    updated = 0
    seen_keys = {(job.fingerprint, job.apply_url) for job in jobs}

    for job in jobs:
        existing = (
            session.query(JobRow)
            .filter_by(fingerprint=job.fingerprint, apply_url=job.apply_url)
            .one_or_none()
        )
        if existing is None:
            session.add(
                JobRow(
                    company=job.company,
                    title=job.title,
                    locations=job.locations,
                    apply_url=job.apply_url,
                    date_posted=job.date_posted,
                    source=job.source,
                    source_job_id=job.source_job_id,
                    sources=job.sources,
                    first_seen=synced_at,
                    last_seen=synced_at,
                    active=True,
                    posting_active=job.posting_active,
                    fingerprint=job.fingerprint,
                )
            )
            inserted += 1
            continue

        if _apply_job_update(existing, job, synced_at):
            updated += 1

    deactivated = 0
    if successful_sources:
        stale_rows = session.query(JobRow).filter(JobRow.active.is_(True)).all()
        for row in stale_rows:
            if (row.fingerprint, row.apply_url) in seen_keys:
                continue
            if not any(source in successful_sources for source in row.sources):
                continue
            row.active = False
            deactivated += 1

    session.commit()
    logger.info(
        "Sync upsert complete: %d inserted, %d updated, %d deactivated",
        inserted,
        updated,
        deactivated,
    )
    return inserted, updated, deactivated


def _apply_job_update(row: JobRow, job: Job, synced_at: datetime) -> bool:
    """Refresh an existing row from the latest feed snapshot. Returns True if fields changed."""
    changed = False

    def set_if_different(attr: str, value: object) -> None:
        nonlocal changed
        if getattr(row, attr) != value:
            setattr(row, attr, value)
            changed = True

    set_if_different("company", job.company)
    set_if_different("title", job.title)
    set_if_different("locations", job.locations)
    set_if_different("apply_url", job.apply_url)
    # Never move posted date forward — aggregator recrawls are not new postings.
    if job.date_posted < row.date_posted:
        row.date_posted = job.date_posted
        changed = True
    set_if_different("source", job.source)
    set_if_different("source_job_id", job.source_job_id)
    set_if_different("posting_active", job.posting_active)

    merged_sources = list(dict.fromkeys(row.sources + job.sources))
    set_if_different("sources", merged_sources)

    if not row.active:
        row.active = True
        changed = True

    row.last_seen = synced_at
    return changed


def list_jobs(
    session: Session,
    *,
    in_feed_only: bool = True,
    open_only: bool = True,
    posted_since: datetime | None = None,
    posted_until: datetime | None = None,
    title: str | None = None,
    location: str | None = None,
    q: str | None = None,
) -> list[JobRead]:
    """List jobs with optional filters. All user strings are bound parameters (never raw SQL)."""
    query = session.query(JobRow).order_by(JobRow.date_posted.desc())
    if in_feed_only:
        query = query.filter(JobRow.active.is_(True))
    if open_only:
        query = query.filter(JobRow.posting_active.is_(True))
    if posted_since is not None:
        query = query.filter(JobRow.date_posted >= posted_since)
    if posted_until is not None:
        query = query.filter(JobRow.date_posted <= posted_until)

    title_term = (title or "").strip()
    if title_term:
        # Bound param via ColumnElement.ilike — pattern is a Python value, not SQL text.
        query = query.filter(
            JobRow.title.ilike(_contains_pattern(title_term), escape=_LIKE_ESCAPE)
        )

    location_term = (location or "").strip()
    if location_term:
        # Match city/location substrings against the locations array without string-building SQL.
        locations_text = func.array_to_string(JobRow.locations, literal(" "))
        query = query.filter(
            locations_text.ilike(_contains_pattern(location_term), escape=_LIKE_ESCAPE)
        )

    search_term = (q or "").strip()
    if search_term:
        pattern = _contains_pattern(search_term)
        query = query.filter(
            or_(
                JobRow.title.ilike(pattern, escape=_LIKE_ESCAPE),
                JobRow.company.ilike(pattern, escape=_LIKE_ESCAPE),
            )
        )

    rows = query.all()
    return [_row_to_schema(row) for row in rows]


def _row_to_schema(row: JobRow) -> JobRead:
    return JobRead(
        id=row.id,
        company=row.company,
        title=row.title,
        locations=row.locations,
        apply_url=row.apply_url,
        date_posted=row.date_posted,
        source=row.source,
        source_job_id=row.source_job_id,
        sources=row.sources,
        first_seen=row.first_seen,
        last_seen=row.last_seen,
        active=row.active,
        posting_active=row.posting_active,
        fingerprint=row.fingerprint,
    )
