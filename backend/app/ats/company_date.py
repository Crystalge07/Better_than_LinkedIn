"""Overlay date_posted and apply_url from the company career posting.

Community feeds (WarpJobs / AI Infra Jobs, SpeedyApply, Simplify, …) often
stamp when *they* listed the role and point Apply at a hosted ATS board.
Prefer:

1. Greenhouse / Lever / Ashby public JSON — first-published time and the
   company's own `absolute_url` / `hostedUrl` / `jobUrl` when that is a
   career-site posting (e.g. stripe.com/jobs/…, not job-boards.greenhouse.io)
2. A matching company-board row already fetched this sync (Workday, etc.)
3. Tesla's public careers JSON, when it includes a published timestamp
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.ats.ashby import ashby_jobs_url
from app.ats.greenhouse import greenhouse_jobs_url
from app.ats.job_url import (
    AtsJobRef,
    canonical_company_apply_url,
    parse_ats_job_ref,
    posting_identity,
    tesla_job_id,
)
from app.ats.lever import lever_jobs_url
from app.ats.posted_on import parse_iso_datetime
from app.normalize.apply_url import pick_preferred_apply_url
from app.schemas.job import Job

logger = logging.getLogger(__name__)

_SENTINEL = datetime.min.replace(tzinfo=timezone.utc)
_COMPANY_BOARD_PREFIXES = ("greenhouse:", "lever:", "ashby:", "workday:")
_TESLA_BOARD_URL = "https://www.tesla.com/cua-api/apps/careers/state"
_TESLA_DATE_KEYS = (
    "datePosted",
    "postedOn",
    "publishedAt",
    "first_published",
    "createdAt",
    "listedDate",
    "published",
    "dp",
)


@dataclass(frozen=True)
class AtsPosting:
    date_posted: datetime | None
    apply_url: str


def overlay_company_posted_dates(jobs: list[Job], *, fetch_json) -> list[Job]:
    """Rewrite date_posted and apply_url from the company career posting when possible."""
    jobs = _overlay_from_ats_apis(jobs, fetch_json)
    jobs = _overlay_from_board_siblings(jobs)
    jobs = _overlay_from_tesla_board(jobs, fetch_json)
    return jobs


def _overlay_from_ats_apis(jobs: list[Job], fetch_json) -> list[Job]:
    refs = [
        None
        if job.source.startswith(_COMPANY_BOARD_PREFIXES)
        else parse_ats_job_ref(job.apply_url)
        for job in jobs
    ]
    board_postings: dict[tuple[str, str], dict[str, AtsPosting]] = {}
    for ref in {item for item in refs if item is not None and item.board}:
        key = (ref.ats, ref.board.lower())
        if key in board_postings:
            continue
        try:
            board_postings[key] = _postings_for_board(ref, fetch_json)
        except Exception:
            logger.exception("Failed to load %s board postings for %s", ref.ats, ref.board)
            board_postings[key] = {}

    by_job_id = _index_postings_by_job_id(board_postings)

    updated: list[Job] = []
    replaced_dates = 0
    replaced_urls = 0
    for job, ref in zip(jobs, refs, strict=True):
        posting = _posting_for_ref(ref, board_postings, by_job_id) if ref else None
        if posting is None:
            updated.append(job)
            continue
        changes: dict[str, object] = {}
        if posting.date_posted is not None and posting.date_posted != job.date_posted:
            changes["date_posted"] = posting.date_posted
            replaced_dates += 1
        preferred = _preferred_apply_url(job.apply_url, posting.apply_url, job.title)
        if preferred != job.apply_url:
            changes["apply_url"] = preferred
            replaced_urls += 1
        updated.append(job.model_copy(update=changes) if changes else job)
    if replaced_dates or replaced_urls:
        logger.info(
            "Overlaid company postings: dates=%d urls=%d",
            replaced_dates,
            replaced_urls,
        )
    return updated


def _overlay_from_board_siblings(jobs: list[Job]) -> list[Job]:
    """Copy posted dates and fuller career URLs from company-board rows onto feed rows."""
    dates: dict[tuple[str, ...], datetime] = {}
    urls: dict[tuple[str, ...], str] = {}
    for job in jobs:
        if not job.source.startswith(_COMPANY_BOARD_PREFIXES):
            continue
        for ident in _identity_keys(job.apply_url):
            previous = dates.get(ident)
            if previous is None or job.date_posted < previous:
                dates[ident] = job.date_posted
            current_url = urls.get(ident)
            if current_url is None:
                urls[ident] = job.apply_url
            else:
                urls[ident] = pick_preferred_apply_url([current_url, job.apply_url])
    if not dates and not urls:
        return jobs

    updated: list[Job] = []
    replaced = 0
    for job in jobs:
        if job.source.startswith(_COMPANY_BOARD_PREFIXES):
            updated.append(job)
            continue
        posted = None
        url = None
        for key in _identity_keys(job.apply_url):
            if posted is None:
                posted = dates.get(key)
            if url is None:
                url = urls.get(key)
        if posted is None and url is None:
            updated.append(job)
            continue
        changes: dict[str, object] = {}
        if posted is not None and posted != job.date_posted:
            changes["date_posted"] = posted
        if url:
            preferred = _preferred_apply_url(job.apply_url, url, job.title)
            if preferred != job.apply_url:
                changes["apply_url"] = preferred
        if changes:
            replaced += 1
            updated.append(job.model_copy(update=changes))
        else:
            updated.append(job)
    if replaced:
        logger.info("Copied company-board posting fields onto %d feed jobs", replaced)
    return updated


def _overlay_from_tesla_board(jobs: list[Job], fetch_json) -> list[Job]:
    tesla_ids = {tesla_job_id(job.apply_url) for job in jobs}
    tesla_ids.discard(None)
    if not tesla_ids:
        return jobs
    try:
        payload = fetch_json(_TESLA_BOARD_URL)
    except Exception:
        logger.warning("Tesla careers JSON unavailable; leaving feed dates for Tesla jobs")
        return jobs
    dates = _tesla_dates(payload)
    if not dates:
        return jobs

    updated: list[Job] = []
    replaced = 0
    for job in jobs:
        job_id = tesla_job_id(job.apply_url)
        posted = dates.get(job_id) if job_id else None
        if posted is None:
            updated.append(job)
            continue
        if posted != job.date_posted:
            replaced += 1
        updated.append(job.model_copy(update={"date_posted": posted}))
    if replaced:
        logger.info("Overlaid Tesla careers posted dates on %d jobs", replaced)
    return updated


def _postings_for_board(ref: AtsJobRef, fetch_json) -> dict[str, AtsPosting]:
    if ref.ats == "greenhouse":
        return _greenhouse_postings(fetch_json(greenhouse_jobs_url(ref.board)))
    if ref.ats == "lever":
        return _lever_postings(fetch_json(lever_jobs_url(ref.board)))
    if ref.ats == "ashby":
        return _ashby_postings(fetch_json(ashby_jobs_url(ref.board)))
    return {}


def _greenhouse_postings(payload: dict | list) -> dict[str, AtsPosting]:
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        return {}
    postings: dict[str, AtsPosting] = {}
    for item in raw_jobs:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        postings[str(item["id"])] = AtsPosting(
            date_posted=_parse_timestamp(item.get("first_published")),
            apply_url=str(item.get("absolute_url") or "").strip(),
        )
    return postings


def _lever_postings(payload: list | dict) -> dict[str, AtsPosting]:
    raw_jobs = payload if isinstance(payload, list) else payload.get("data", [])
    if not isinstance(raw_jobs, list):
        return {}
    postings: dict[str, AtsPosting] = {}
    for item in raw_jobs:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        postings[str(item["id"])] = AtsPosting(
            date_posted=_parse_timestamp(item.get("createdAt")),
            apply_url=str(item.get("hostedUrl") or item.get("applyUrl") or "").strip(),
        )
    return postings


def _ashby_postings(payload: dict | list) -> dict[str, AtsPosting]:
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        return {}
    postings: dict[str, AtsPosting] = {}
    for item in raw_jobs:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        postings[str(item["id"])] = AtsPosting(
            date_posted=_parse_timestamp(item.get("publishedAt")),
            apply_url=str(item.get("jobUrl") or item.get("applyUrl") or "").strip(),
        )
    return postings


def _index_postings_by_job_id(
    board_postings: dict[tuple[str, str], dict[str, AtsPosting]],
) -> dict[tuple[str, str], AtsPosting]:
    by_id: dict[tuple[str, str], AtsPosting] = {}
    for (ats, _board), postings in board_postings.items():
        for job_id, posting in postings.items():
            by_id[(ats, job_id)] = posting
    return by_id


def _posting_for_ref(
    ref: AtsJobRef,
    board_postings: dict[tuple[str, str], dict[str, AtsPosting]],
    by_job_id: dict[tuple[str, str], AtsPosting],
) -> AtsPosting | None:
    if ref.board:
        found = board_postings.get((ref.ats, ref.board.lower()), {}).get(ref.job_id)
        if found is not None:
            return found
    return by_job_id.get((ref.ats, ref.job_id))


def _identity_keys(url: str) -> list[tuple[str, ...]]:
    keys: list[tuple[str, ...]] = []
    ident = posting_identity(url)
    if ident is not None:
        keys.append(ident)
    ref = parse_ats_job_ref(url)
    if ref is not None and ref.board:
        short = (ref.ats, str(ref.job_id).lower())
        if short not in keys:
            keys.append(short)
    return keys


def _preferred_apply_url(current: str, ats_url: str, title: str) -> str:
    candidates = [url for url in (current.strip(), ats_url.strip()) if url]
    if not candidates:
        return current
    return canonical_company_apply_url(pick_preferred_apply_url(candidates), title)


def _tesla_dates(payload: dict | list) -> dict[str, datetime]:
    listings = payload.get("listings", payload) if isinstance(payload, dict) else payload
    if not isinstance(listings, list):
        return {}
    dates: dict[str, datetime] = {}
    for item in listings:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        posted = None
        for key in _TESLA_DATE_KEYS:
            posted = _parse_timestamp(item.get(key))
            if posted is not None:
                break
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
