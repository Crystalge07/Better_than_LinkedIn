"""Parse a job apply URL into a Greenhouse / Lever / Ashby posting identity."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class AtsJobRef:
    ats: str
    board: str
    job_id: str


def parse_ats_job_ref(url: str) -> AtsJobRef | None:
    """Return board + job id when `url` is a public ATS posting, else None."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    query = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}

    if "greenhouse.io" in host:
        return _greenhouse_ref(host, parts, query)
    if host in {"jobs.lever.co", "api.lever.co"}:
        return _lever_ref(parts)
    if host in {"jobs.ashbyhq.com", "api.ashbyhq.com"}:
        return _ashby_ref(parts)
    return None


def _greenhouse_ref(host: str, parts: list[str], query: dict[str, str]) -> AtsJobRef | None:
    board = (query.get("for") or "").strip()
    job_id = (
        query.get("gh_jid") or query.get("token") or query.get("t") or ""
    ).strip()
    path = parts
    if path[:2] == ["v1", "boards"] and len(path) >= 4 and path[3] == "jobs":
        board = board or path[2]
        job_id = job_id or (path[4] if len(path) > 4 else "")
    elif "jobs" in path:
        idx = path.index("jobs")
        if idx > 0:
            board = board or path[idx - 1]
        if idx + 1 < len(path):
            job_id = job_id or path[idx + 1]
    elif not board and path:
        board = path[0]
    if not board or not job_id or not job_id.isdigit():
        return None
    return AtsJobRef(ats="greenhouse", board=board, job_id=job_id)


def _lever_ref(parts: list[str]) -> AtsJobRef | None:
    parts = [part for part in parts if part.lower() not in {"v0", "postings", "apply"}]
    if len(parts) < 2:
        return None
    return AtsJobRef(ats="lever", board=parts[0], job_id=parts[1])


def _ashby_ref(parts: list[str]) -> AtsJobRef | None:
    parts = [part for part in parts if part.lower() not in {"posting-api", "job-board", "job"}]
    if len(parts) < 2:
        return None
    return AtsJobRef(ats="ashby", board=parts[0], job_id=parts[1])
