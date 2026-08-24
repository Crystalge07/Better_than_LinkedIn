"""Ashby job-board JSON mapper."""

from datetime import datetime
from urllib.parse import quote

from app.ats.early_career import is_early_career
from app.ats.map_job import job_from_board
from app.ats.posted_on import parse_iso_datetime
from app.schemas.job import Job


def ashby_jobs_url(board: str) -> str:
    return f"https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe='')}"


def map_ashby_jobs(
    payload: dict | list,
    *,
    company: str,
    source: str,
    seen_at: datetime,
) -> list[Job]:
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        raise ValueError("Ashby payload missing jobs list")

    jobs: list[Job] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        if item.get("isListed") is False or item.get("isListed") is False:
            continue
        title = str(item.get("title") or "")
        if not is_early_career(title):
            continue
        location = item.get("location")
        extra = item.get("secondaryLocations") or []
        locations = [location] if location else []
        for loc in extra:
            if isinstance(loc, dict) and loc.get("location"):
                locations.append(loc["location"])
            elif isinstance(loc, str):
                locations.append(loc)
        date_posted = parse_iso_datetime(item.get("publishedAt"), fallback=seen_at)
        job = job_from_board(
            company=company,
            title=title,
            locations=[str(loc) for loc in locations if loc],
            apply_url=str(item.get("jobUrl") or item.get("applyUrl") or ""),
            date_posted=date_posted,
            source=source,
            source_job_id=str(item.get("id") or ""),
            seen_at=seen_at,
        )
        if job is not None:
            jobs.append(job)
    return jobs
