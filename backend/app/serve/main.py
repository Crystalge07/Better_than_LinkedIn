import logging
from datetime import date, datetime, time, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.schemas.application import AppliedJobIn, AppliedJobPatch, AppliedJobRead
from app.schemas.job import JobRead
from app.store.applications import (
    delete_applied_job,
    list_applied_jobs,
    patch_applied_job,
    upsert_applied_job,
)
from app.store.database import get_session, init_db
from app.store.repository import list_jobs

logger = logging.getLogger(__name__)

app = FastAPI(title="Job Aggregator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _start_of_day_utc(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _end_of_day_utc(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


@app.get("/api/jobs", response_model=list[JobRead])
def get_jobs(
    active_only: bool = True,
    open_only: bool = True,
    posted_within_days: int = Query(default=30, ge=1),
    posted_after: date | None = None,
    posted_before: date | None = None,
    title: str | None = None,
    location: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
) -> list[JobRead]:
    """Return filtered open, in-feed postings.

    Filtering is applied in Postgres via bound parameters — never client-side.
    """
    if posted_after is not None or posted_before is not None:
        posted_since = _start_of_day_utc(posted_after) if posted_after is not None else None
        posted_until = _end_of_day_utc(posted_before) if posted_before is not None else None
    else:
        posted_since = datetime.now(timezone.utc) - timedelta(days=posted_within_days)
        posted_until = None

    return list_jobs(
        session,
        in_feed_only=active_only,
        open_only=open_only,
        posted_since=posted_since,
        posted_until=posted_until,
        title=title,
        location=location,
        q=q,
    )


@app.get("/api/applications", response_model=list[AppliedJobRead])
def get_applications(session: Session = Depends(get_session)) -> list[AppliedJobRead]:
    return list_applied_jobs(session)


@app.post("/api/applications", response_model=AppliedJobRead)
def post_application(
    incoming: AppliedJobIn,
    session: Session = Depends(get_session),
) -> AppliedJobRead:
    return upsert_applied_job(session, incoming)


@app.patch("/api/applications", response_model=AppliedJobRead)
def patch_application(
    patch: AppliedJobPatch,
    id: str = Query(..., min_length=1),
    session: Session = Depends(get_session),
) -> AppliedJobRead:
    updated = patch_applied_job(session, id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return updated


@app.delete("/api/applications")
def remove_application(
    id: str = Query(..., min_length=1),
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    if not delete_applied_job(session, id):
        raise HTTPException(status_code=404, detail="Application not found")
    return {"ok": True}
