"""Greenhouse job-board JSON mapper."""

from datetime import datetime

from app.ats.early_career import is_early_career
from app.ats.map_job import job_from_board
from app.ats.posted_on import parse_iso_datetime
from app.schemas.job import Job


def greenhouse_jobs_url(board: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"


def map_greenhouse_jobs(
    payload: dict | list,
    *,
    company: str,
    source: str,
    seen_at: datetime,
) -> list[Job]:
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        raise ValueError("Greenhouse payload missing jobs list")

    jobs: list[Job] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        if not is_early_career(title):
            continue
        location = item.get("location") or {}
        location_name = location.get("name") if isinstance(location, dict) else None
        date_posted = parse_iso_datetime(
            item.get("first_published") or item.get("updated_at"),
            fallback=seen_at,
        )
        job = job_from_board(
            company=company,
            title=title,
            locations=[location_name] if location_name else [],
            apply_url=str(item.get("absolute_url") or ""),
            date_posted=date_posted,
            source=source,
            source_job_id=str(item.get("id") or ""),
            seen_at=seen_at,
        )
        if job is not None:
            jobs.append(job)
    return jobs
