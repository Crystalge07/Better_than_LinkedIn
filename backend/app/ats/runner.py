"""Fetch early-career jobs from configured company career boards."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.ats.ashby import ashby_jobs_url, map_ashby_jobs
from app.ats.greenhouse import greenhouse_jobs_url, map_greenhouse_jobs
from app.ats.lever import lever_jobs_url, map_lever_jobs
from app.ats.registry import CompanyBoard, load_company_boards
from app.ats.workday import (
    WORKDAY_MAX_PAGES,
    WORKDAY_PAGE_SIZE,
    WORKDAY_SEARCHES,
    map_workday_page,
    workday_jobs_url,
    workday_page_payload,
)
from app.schemas.job import Job

logger = logging.getLogger(__name__)


def fetch_company_jobs(fetch_json, post_json) -> tuple[list[Job], set[str], int, int]:
    """Return (jobs, successful source tags, boards_ok, boards_failed)."""
    jobs: list[Job] = []
    successful: set[str] = set()
    ok = 0
    failed = 0
    seen_at = datetime.now(timezone.utc)

    for company in load_company_boards():
        try:
            batch = _fetch_one(company, fetch_json, post_json, seen_at)
        except Exception:
            logger.exception("Company board failed: %s (%s)", company.name, company.source_tag)
            failed += 1
            continue
        ok += 1
        successful.add(company.source_tag)
        jobs.extend(batch)
        logger.info("Normalized %d early-career jobs from %s", len(batch), company.source_tag)

    return jobs, successful, ok, failed


def _fetch_one(company: CompanyBoard, fetch_json, post_json, seen_at: datetime) -> list[Job]:
    if company.ats == "greenhouse":
        payload = fetch_json(greenhouse_jobs_url(company.board or ""))
        return map_greenhouse_jobs(
            payload, company=company.name, source=company.source_tag, seen_at=seen_at
        )
    if company.ats == "lever":
        payload = fetch_json(lever_jobs_url(company.board or ""))
        return map_lever_jobs(
            payload, company=company.name, source=company.source_tag, seen_at=seen_at
        )
    if company.ats == "ashby":
        payload = fetch_json(ashby_jobs_url(company.board or ""))
        return map_ashby_jobs(
            payload, company=company.name, source=company.source_tag, seen_at=seen_at
        )
    if company.ats == "workday":
        return _fetch_workday(company, post_json, seen_at)
    raise ValueError(f"Unsupported ats: {company.ats}")


def _fetch_workday(company: CompanyBoard, post_json, seen_at: datetime) -> list[Job]:
    url = workday_jobs_url(company.parsed)
    headers = {"Referer": f"https://{company.parsed.host}/{company.parsed.site}"}
    jobs: list[Job] = []
    seen_ids: set[str] = set()
    for search_text in WORKDAY_SEARCHES:
        for page in range(WORKDAY_MAX_PAGES):
            payload = workday_page_payload(offset=page * WORKDAY_PAGE_SIZE, search_text=search_text)
            data = post_json(url, payload, extra_headers=headers)
            if not isinstance(data, dict):
                break
            raw_page = data.get("jobPostings") or []
            page_jobs = map_workday_page(
                data,
                company=company.name,
                source=company.source_tag,
                board=company.parsed,
                seen_at=seen_at,
            )
            for job in page_jobs:
                if job.source_job_id in seen_ids:
                    continue
                seen_ids.add(job.source_job_id)
                jobs.append(job)
            if len(raw_page) < WORKDAY_PAGE_SIZE:
                break
            total = int(data.get("total") or 0)
            if total and (page + 1) * WORKDAY_PAGE_SIZE >= total:
                break
    return jobs
