import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.schemas.job import JobRead
from app.store.database import get_session, init_db
from app.store.repository import list_jobs

logger = logging.getLogger(__name__)

app = FastAPI(title="Job Aggregator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


@app.get("/api/jobs", response_model=list[JobRead])
def get_jobs(
    active_only: bool = True,
    open_only: bool = True,
    posted_within_days: int = 30,
    session: Session = Depends(get_session),
) -> list[JobRead]:
    """Return in-feed, open postings from the recent window."""
    posted_since = datetime.now(timezone.utc) - timedelta(days=posted_within_days)
    return list_jobs(
        session,
        in_feed_only=active_only,
        open_only=open_only,
        posted_since=posted_since,
    )
