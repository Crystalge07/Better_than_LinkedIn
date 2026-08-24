"""Lever job-board JSON mapper."""

from datetime import datetime

from app.ats.early_career import is_early_career
from app.ats.map_job import job_from_board
from app.ats.posted_on import parse_iso_datetime
from app.schemas.job import Job


def lever_jobs_url(board: str) -> str:
    return f"https://api.lever.co/v0/postings/{board}?mode=json"


def map_lever_jobs(
    payload: list | dict,
    *,
    company: str,
    source: str,
    seen_at: datetime,
) -> list[Job]:
    raw_jobs = payload if isinstance(payload, list) else payload.get("data", [])
    if not isinstance(raw_jobs, list):
        raise ValueError("Lever payload missing jobs list")

    jobs: list[Job] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        title = str(item.get("text") or item.get("title") or "")
        if not is_early_career(title):
            continue
        categories = item.get("categories") or {}
        location = categories.get("location") if isinstance(categories, dict) else None
        date_posted = parse_iso_datetime(item.get("createdAt"), fallback=seen_at)
        job = job_from_board(
            company=company,
            title=title,
            locations=[location] if location else [],
            apply_url=str(item.get("hostedUrl") or item.get("applyUrl") or ""),
            date_posted=date_posted,
            source=source,
            source_job_id=str(item.get("id") or ""),
            seen_at=seen_at,
        )
        if job is not None:
            jobs.append(job)
    return jobs
