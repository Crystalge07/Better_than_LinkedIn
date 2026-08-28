"""Parse a job apply URL into a Greenhouse / Lever / Ashby posting identity."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

_GREENHOUSE_IDENTIFIER = re.compile(r"^gh-(.+)-(\d+)$", re.IGNORECASE)
_ASHBY_IDENTIFIER = re.compile(
    r"^ash-(.+)-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)
_LEVER_IDENTIFIER = re.compile(r"^lv-(.+)-([0-9a-f-]{8,})$", re.IGNORECASE)


@dataclass(frozen=True)
class AtsJobRef:
    ats: str
    board: str
    job_id: str


def parse_ats_job_ref(url: str) -> AtsJobRef | None:
    """Return board + job id when `url` is a public ATS posting, else None.

    Also matches company career pages that embed Greenhouse (`gh_jid` / `for`).
    """
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

    job_id = (query.get("gh_jid") or query.get("token") or query.get("t") or "").strip()
    board = (query.get("for") or "").strip()
    if job_id.isdigit():
        return AtsJobRef(ats="greenhouse", board=board, job_id=job_id)
    return None


def parse_ats_identifier(value: str) -> AtsJobRef | None:
    """Parse aggregator identifiers like `gh-togetherai-5214645007`."""
    text = value.strip()
    greenhouse = _GREENHOUSE_IDENTIFIER.fullmatch(text)
    if greenhouse:
        return AtsJobRef(ats="greenhouse", board=greenhouse.group(1), job_id=greenhouse.group(2))
    ashby = _ASHBY_IDENTIFIER.fullmatch(text)
    if ashby:
        return AtsJobRef(ats="ashby", board=ashby.group(1), job_id=ashby.group(2))
    lever = _LEVER_IDENTIFIER.fullmatch(text)
    if lever:
        return AtsJobRef(ats="lever", board=lever.group(1), job_id=lever.group(2))
    return None


def canonical_ats_apply_url(ref: AtsJobRef) -> str:
    if ref.ats == "greenhouse":
        return f"https://job-boards.greenhouse.io/{ref.board}/jobs/{ref.job_id}"
    if ref.ats == "lever":
        return f"https://jobs.lever.co/{ref.board}/{ref.job_id}"
    if ref.ats == "ashby":
        return f"https://jobs.ashbyhq.com/{ref.board}/{ref.job_id}"
    raise ValueError(f"Unsupported ATS {ref.ats}")


_TESLA_HOSTS = {"tesla.com", "www.tesla.com"}
_WORKDAY_REQ = re.compile(r"(JR\d+|[A-Za-z]*R\d+)$", re.IGNORECASE)


def tesla_job_id(url: str) -> str | None:
    """Numeric Tesla requisition id from a careers.tesla.com posting URL."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host not in _TESLA_HOSTS:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4 or [part.lower() for part in parts[:3]] != ["careers", "search", "job"]:
        return None
    tail = parts[3]
    if tail.isdigit():
        return tail
    maybe_id = tail.rsplit("-", 1)[-1]
    return maybe_id if maybe_id.isdigit() else None


def canonical_tesla_apply_url(url: str, title: str) -> str:
    """Tesla job pages need `/careers/search/job/{slug}-{id}`, not the id-only search URL."""
    job_id = tesla_job_id(url)
    if not job_id:
        return url.strip()
    slug = _slugify(title) or "job"
    return f"https://www.tesla.com/careers/search/job/{slug}-{job_id}"


def canonical_company_apply_url(url: str, title: str) -> str:
    """Normalize an employer posting URL without sending the user to a middleman board."""
    return canonical_tesla_apply_url(url.strip(), title)


def workday_posting_key(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if "myworkdayjobs.com" not in host and "myworkdaysite.com" not in host:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None
    tail = parts[-1]
    match = _WORKDAY_REQ.search(tail)
    req = (match.group(1) if match else tail).lstrip("_").lower()
    if not req:
        return None
    return (host, req)


def posting_identity(url: str) -> tuple[str, ...] | None:
    """Stable posting key used to copy company-board dates onto feed rows."""
    ref = parse_ats_job_ref(url)
    if ref is not None:
        if ref.board:
            return (ref.ats, ref.board.lower(), str(ref.job_id).lower())
        return (ref.ats, str(ref.job_id).lower())
    tesla = tesla_job_id(url)
    if tesla is not None:
        return ("tesla", tesla)
    workday = workday_posting_key(url)
    if workday is not None:
        return ("workday", workday[0], workday[1])
    return None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


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
