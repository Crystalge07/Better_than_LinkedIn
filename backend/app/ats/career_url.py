"""Infer ATS type and board identifiers from a public career URL."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

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
    path_parts = [part for part in parsed.path.split("/") if part]

    if "greenhouse.io" in host:
        board = _greenhouse_board(host, path_parts)
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
        return _parse_workday(host, path_parts, url)

    raise ValueError(f"Unsupported career URL (need Greenhouse, Lever, Ashby, or Workday): {url}")


def _greenhouse_board(host: str, path_parts: list[str]) -> str | None:
    if "boards-api.greenhouse.io" in host:
        parts = path_parts
        if parts[:2] == ["v1", "boards"] and len(parts) >= 3:
            return parts[2]
        return None
    if path_parts:
        return path_parts[0]
    return None


def _skip_api_prefix(path_parts: list[str], prefixes: set[str]) -> str | None:
    parts = [part for part in path_parts if part.lower() not in prefixes]
    return parts[0] if parts else None


def _parse_workday(host: str, path_parts: list[str], url: str) -> ParsedBoard:
    tenant = host.split(".")[0]
    parts = [part for part in path_parts if part.lower() not in _LANGUAGE_PREFIXES]
    parts = [part for part in parts if part.lower() not in {"wday", "cxs", "jobs", "job"}]
    if parts and parts[0].lower() == tenant.lower():
        parts = parts[1:]
    if not parts:
        raise ValueError(f"Could not parse Workday site slug from {url}")
    return ParsedBoard(ats="workday", host=host, tenant=tenant, site=parts[0], board=parts[0])
