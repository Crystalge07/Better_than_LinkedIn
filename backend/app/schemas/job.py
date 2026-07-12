"""Internal Job schema — the contract across ingestion and API."""

from datetime import datetime

from pydantic import BaseModel, Field


class Job(BaseModel):
    company: str
    title: str
    locations: list[str]
    apply_url: str
    date_posted: datetime
    source: str = Field(description="Feed tag identifying which adapter/feed produced this row")
    source_job_id: str = Field(description="Native id from the source feed JSON")
    sources: list[str] = Field(description="All feeds this job was found in, after dedupe")
    first_seen: datetime
    last_seen: datetime
    active: bool = Field(description="True while the job is still present in any feed")
    posting_active: bool = Field(
        description="Feed flag: True if applications are open on the source site"
    )
    fingerprint: str = Field(description="Dedupe key; full logic added in step 3")


class JobRead(Job):
    id: int
