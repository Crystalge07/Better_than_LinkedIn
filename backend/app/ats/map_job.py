"""Build a Job from ATS fields using the shared fingerprint contract."""

from datetime import datetime

from app.normalize.fingerprint import compute_fingerprint
from app.schemas.job import Job


def job_from_board(
    *,
    company: str,
    title: str,
    locations: list[str],
    apply_url: str,
    date_posted: datetime,
    source: str,
    source_job_id: str,
    seen_at: datetime,
    posting_active: bool = True,
) -> Job | None:
    company = company.strip()
    title = title.strip()
    apply_url = apply_url.strip()
    source_job_id = source_job_id.strip()[:64]
    if not company or not title or not apply_url or not source_job_id:
        return None
    cleaned_locations = [loc.strip() for loc in locations if loc and loc.strip()]
    if not cleaned_locations:
        cleaned_locations = ["Unknown"]
    return Job(
        company=company,
        title=title,
        locations=cleaned_locations,
        apply_url=apply_url,
        date_posted=date_posted,
        source=source,
        source_job_id=source_job_id,
        sources=[source],
        first_seen=seen_at,
        last_seen=seen_at,
        active=True,
        posting_active=posting_active,
        fingerprint=compute_fingerprint(company, title, cleaned_locations),
    )
