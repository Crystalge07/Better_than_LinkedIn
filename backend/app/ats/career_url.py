"""Infer ATS type and board identifiers from a public career URL."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, quote, unquote, urlparse

_LANGUAGE_PREFIXES = {
    "en",
    "en-us",
    "en-gb",
    "en-ca",
    "fr",
    "fr-fr",
    "de",
    "de-de",
    "es",
    "es-es",
    "zh-cn",
    "ja-jp",
}

_GREENHOUSE_PATH_SKIP = {"embed", "job_board", "job_app", "jobs", "job"}


@dataclass(frozen=True)
class ParsedBoard:
    ats: str
    board: str | None = None
    host: str | None = None
    tenant: str | None = None
    site: str | None = None


def parse_career_url(url: str) -> ParsedBoard:
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    query = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}

    if "greenhouse.io" in host:
        board = _greenhouse_board(host, path_parts, query)
        if not board:
            raise ValueError(f"Could not parse Greenhouse board from {url}")
        return ParsedBoard(ats="greenhouse", board=board)

    if host in {"jobs.lever.co", "api.lever.co"}:
        board = _skip_api_prefix(path_parts, {"v0", "postings"})
        if not board:
            raise ValueError(f"Could not parse Lever board from {url}")
        return ParsedBoard(ats="lever", board=board)

    if host in {"jobs.ashbyhq.com", "api.ashbyhq.com"}:
        board = _skip_api_prefix(path_parts, {"posting-api", "job-board"})
        if not board:
            raise ValueError(f"Could not parse Ashby board from {url}")
        return ParsedBoard(ats="ashby", board=board)

    if "myworkdayjobs.com" in host:
        return _parse_workday_jobs(host, path_parts, url)

    if "myworkdaysite.com" in host:
        return _parse_workday_site(host, path_parts, url)

    raise ValueError(f"Unsupported career URL (need Greenhouse, Lever, Ashby, or Workday): {url}")


def canonical_career_url(board: ParsedBoard) -> str:
    """Board root URL used in companies.json (not a single job posting)."""
    if board.ats == "greenhouse":
        return f"https://job-boards.greenhouse.io/{quote(board.board or '', safe='')}"
    if board.ats == "lever":
        return f"https://jobs.lever.co/{quote(board.board or '', safe='')}"
    if board.ats == "ashby":
        return f"https://jobs.ashbyhq.com/{quote(board.board or '', safe='')}"
    if board.ats == "workday":
        if not board.host or not board.site:
            raise ValueError("Workday board is missing host/site")
        if "myworkdaysite.com" in board.host:
            if not board.tenant:
                raise ValueError("Workday myworkdaysite board is missing tenant")
            return f"https://{board.host}/recruiting/{board.tenant}/{board.site}"
        return f"https://{board.host}/{board.site}"
    raise ValueError(f"Unsupported ats {board.ats}")


def board_identity(board: ParsedBoard) -> tuple[str, ...]:
    """Stable key for de-duplicating company rows."""
    if board.ats == "workday":
        return (
            "workday",
            (board.host or "").lower(),
            (board.tenant or "").lower(),
            (board.site or "").lower(),
        )
    return (board.ats, (board.board or "").lower())


def _greenhouse_board(host: str, path_parts: list[str], query: dict[str, str]) -> str | None:
    for_param = (query.get("for") or "").strip()
    if for_param:
        return for_param
    if "boards-api.greenhouse.io" in host:
        parts = path_parts
        if parts[:2] == ["v1", "boards"] and len(parts) >= 3:
            return parts[2]
        return None
    parts = [part for part in path_parts if part.lower() not in _GREENHOUSE_PATH_SKIP]
    return parts[0] if parts else None


def _skip_api_prefix(path_parts: list[str], prefixes: set[str]) -> str | None:
    parts = [part for part in path_parts if part.lower() not in prefixes]
    return parts[0] if parts else None


def _parse_workday_jobs(host: str, path_parts: list[str], url: str) -> ParsedBoard:
    tenant = host.split(".")[0]
    parts = [part for part in path_parts if part.lower() not in _LANGUAGE_PREFIXES]
    parts = [part for part in parts if part.lower() not in {"wday", "cxs", "jobs", "job"}]
    if parts and parts[0].lower() == tenant.lower():
        parts = parts[1:]
    if not parts:
        raise ValueError(f"Could not parse Workday site slug from {url}")
    return ParsedBoard(ats="workday", host=host, tenant=tenant, site=parts[0], board=parts[0])


def _parse_workday_site(host: str, path_parts: list[str], url: str) -> ParsedBoard:
    parts = [part for part in path_parts if part.lower() not in _LANGUAGE_PREFIXES]
    parts = [part for part in parts if part.lower() not in {"wday", "cxs", "jobs", "job"}]
    if parts and parts[0].lower() == "recruiting":
        parts = parts[1:]
    if len(parts) < 2:
        raise ValueError(f"Could not parse Workday tenant/site from {url}")
    tenant, site = parts[0], parts[1]
    return ParsedBoard(ats="workday", host=host, tenant=tenant, site=site, board=site)
