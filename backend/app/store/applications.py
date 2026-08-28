from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas.application import AppliedJobIn, AppliedJobPatch, AppliedJobRead
from app.store.models import AppliedJobRow


def _prefer(existing: str, incoming: str) -> str:
    return existing or incoming


def _row_to_read(row: AppliedJobRow) -> AppliedJobRead:
    return AppliedJobRead(
        id=row.id,
        firm=row.firm,
        location=row.location,
        title=row.title,
        link=row.link,
        applied_at=row.applied_at,
    )


def list_applied_jobs(session: Session) -> list[AppliedJobRead]:
    rows = session.query(AppliedJobRow).order_by(AppliedJobRow.applied_at.desc()).all()
    return [_row_to_read(row) for row in rows]


def upsert_applied_job(session: Session, incoming: AppliedJobIn) -> AppliedJobRead:
    job_id = (incoming.id or incoming.link or "").strip()
    if not job_id:
        job_id = f"manual:{datetime.now(timezone.utc).isoformat()}"
    applied_at = incoming.applied_at or datetime.now(timezone.utc)
    if applied_at.tzinfo is None:
        applied_at = applied_at.replace(tzinfo=timezone.utc)

    row = session.get(AppliedJobRow, job_id)
    if row is None and incoming.link.strip():
        row = (
            session.query(AppliedJobRow)
            .filter(AppliedJobRow.link == incoming.link.strip())
            .one_or_none()
        )
    if row is None:
        row = AppliedJobRow(
            id=job_id,
            firm=incoming.firm.strip(),
            location=incoming.location.strip(),
            title=incoming.title.strip(),
            link=incoming.link.strip(),
            applied_at=applied_at,
        )
        session.add(row)
    else:
        row.firm = _prefer(row.firm, incoming.firm.strip())
        row.location = _prefer(row.location, incoming.location.strip())
        row.title = _prefer(row.title, incoming.title.strip())
        row.link = _prefer(row.link, incoming.link.strip())
    session.commit()
    session.refresh(row)
    return _row_to_read(row)


def patch_applied_job(
    session: Session, job_id: str, patch: AppliedJobPatch
) -> AppliedJobRead | None:
    row = session.get(AppliedJobRow, job_id)
    if row is None:
        return None
    if patch.firm is not None:
        row.firm = patch.firm.strip()
    if patch.location is not None:
        row.location = patch.location.strip()
    if patch.title is not None:
        row.title = patch.title.strip()
    if patch.link is not None:
        row.link = patch.link.strip()
    if patch.applied_at is not None:
        applied_at = patch.applied_at
        if applied_at.tzinfo is None:
            applied_at = applied_at.replace(tzinfo=timezone.utc)
        row.applied_at = applied_at
    session.commit()
    session.refresh(row)
    return _row_to_read(row)


def delete_applied_job(session: Session, job_id: str) -> bool:
    row = session.get(AppliedJobRow, job_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
