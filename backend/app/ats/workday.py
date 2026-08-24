"""Workday public career-site CXS JSON mapper and pagination."""

from datetime import datetime

from app.ats.career_url import ParsedBoard
from app.ats.early_career import is_early_career
from app.ats.map_job import job_from_board
from app.ats.posted_on import parse_workday_posted_on
from app.schemas.job import Job

WORKDAY_PAGE_SIZE = 20
WORKDAY_MAX_PAGES = 5
WORKDAY_SEARCHES = (
    "intern",
    "new grad",
    "co-op",
    "early career",
)


def workday_jobs_url(board: ParsedBoard) -> str:
    if not board.host or not board.tenant or not board.site:
        raise ValueError("Workday board is missing host/tenant/site")
    return f"https://{board.host}/wday/cxs/{board.tenant}/{board.site}/jobs"


def workday_referer_headers(board: ParsedBoard) -> dict[str, str]:
    if board.host and "myworkdaysite.com" in board.host:
        return {"Referer": f"https://{board.host}/recruiting/{board.tenant}/{board.site}"}
    return {"Referer": f"https://{board.host}/{board.site}"}


def workday_apply_url(board: ParsedBoard, external_path: str) -> str:
    path = external_path if external_path.startswith("/") else f"/{external_path}"
    if board.host and "myworkdaysite.com" in board.host:
        return f"https://{board.host}/recruiting/{board.tenant}/{board.site}{path}"
    return f"https://{board.host}/en-US/{board.site}{path}"


def workday_page_payload(*, offset: int, search_text: str) -> dict:
    return {
        "appliedFacets": {},
        "limit": WORKDAY_PAGE_SIZE,
        "offset": offset,
        "searchText": search_text,
    }


def map_workday_page(
    payload: dict,
    *,
    company: str,
    source: str,
    board: ParsedBoard,
    seen_at: datetime,
) -> list[Job]:
    raw_jobs = payload.get("jobPostings") or []
    if not isinstance(raw_jobs, list):
        raise ValueError("Workday payload missing jobPostings list")

    jobs: list[Job] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        if not is_early_career(title):
            continue
        external_path = str(item.get("externalPath") or "")
        bullets = item.get("bulletFields") or []
        source_job_id = str(bullets[0] if bullets else external_path.rsplit("/", 1)[-1])
        job = job_from_board(
            company=company,
            title=title,
            locations=[str(item.get("locationsText") or "")],
            apply_url=workday_apply_url(board, external_path) if external_path else "",
            date_posted=parse_workday_posted_on(item.get("postedOn"), now=seen_at),
            source=source,
            source_job_id=source_job_id,
            seen_at=seen_at,
        )
        if job is not None:
            jobs.append(job)
    return jobs
