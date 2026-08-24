"""Overlay date_posted with the company ATS first-published time.

Community feeds (WarpJobs / AI Infra Jobs, SpeedyApply, Simplify, …) often
stamp when *they* listed the role. When the apply URL is Greenhouse, Lever, or
Ashby, replace that with the posting's first-published / created / published
timestamp from the public board JSON API.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.ats.ashby import ashby_jobs_url
from app.ats.greenhouse import greenhouse_jobs_url
from app.ats.job_url import AtsJobRef, parse_ats_job_ref
from app.ats.lever import lever_jobs_url
from app.ats.posted_on import parse_iso_datetime
from app.schemas.job import Job

logger = logging.getLogger(__name__)

_SENTINEL = datetime.min.replace(tzinfo=timezone.utc)
_COMPANY_BOARD_PREFIXES = ("greenhouse:", "lever:", "ashby:", "workday:")


def overlay_company_posted_dates(jobs: list[Job], *, fetch_json) -> list[Job]:
    """Rewrite date_posted from the company board when the apply URL is an ATS posting."""
    refs = [
        None
        if job.source.startswith(_COMPANY_BOARD_PREFIXES)
        else parse_ats_job_ref(job.apply_url)
        for job in jobs
    ]
    board_dates: dict[tuple[str, str], dict[str, datetime]] = {}
    for ref in {item for item in refs if item is not None}:
        key = (ref.ats, ref.board.lower())
        if key in board_dates:
            continue
        try:
            board_dates[key] = _dates_for_board(ref, fetch_json)
        except Exception:
            logger.exception("Failed to load %s board dates for %s", ref.ats, ref.board)
            board_dates[key] = {}

    updated: list[Job] = []
    replaced = 0
    for job, ref in zip(jobs, refs, strict=True):
        if ref is None:
            updated.append(job)
            continue
        posted = board_dates.get((ref.ats, ref.board.lower()), {}).get(ref.job_id)
        if posted is None:
            updated.append(job)
            continue
        if posted != job.date_posted:
            replaced += 1
        updated.append(job.model_copy(update={"date_posted": posted}))
    if replaced:
        logger.info("Overlaid company-board posted dates on %d jobs", replaced)
    return updated


def _dates_for_board(ref: AtsJobRef, fetch_json) -> dict[str, datetime]:
    if ref.ats == "greenhouse":
        return _greenhouse_dates(fetch_json(greenhouse_jobs_url(ref.board)))
    if ref.ats == "lever":
        return _lever_dates(fetch_json(lever_jobs_url(ref.board)))
    if ref.ats == "ashby":
        return _ashby_dates(fetch_json(ashby_jobs_url(ref.board)))
    return {}


def _greenhouse_dates(payload: dict | list) -> dict[str, datetime]:
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        return {}
    dates: dict[str, datetime] = {}
    for item in raw_jobs:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        posted = _parse_timestamp(item.get("first_published") or item.get("first_published"))
        if posted is None:
            continue
        dates[str(item["id"])] = posted
    return dates


def _lever_dates(payload: list | dict) -> dict[str, datetime]:
    raw_jobs = payload if isinstance(payload, list) else payload.get("data", [])
    if not isinstance(raw_jobs, list):
        return {}
    dates: dict[str, datetime] = {}
    for item in raw_jobs:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        posted = _parse_timestamp(item.get("createdAt") or item.get("createdAt"))
        if posted is None:
            continue
        dates[str(item["id"])] = posted
    return dates


def _ashby_dates(payload: dict | list) -> dict[str, datetime]:
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        return {}
    dates: dict[str, datetime] = {}
    for item in raw_jobs:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        posted = _parse_timestamp(item.get("publishedAt") or item.get("publishedAt"))
        if posted is None:
            continue
        dates[str(item["id"])] = posted
    return dates


def _parse_timestamp(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = parse_iso_datetime(value, fallback=_SENTINEL)
    if parsed == _SENTINEL:
        return None
    return parsed


overlay_company_posted_dates = overlay_company_posted_dates
