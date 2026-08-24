"""Discover company career boards from listing URLs and seed files."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.ats.career_url import ParsedBoard, board_identity, canonical_career_url, parse_career_url
from app.normalize.adapters.simplify_internships import FEED_URL as SIMPLIFY_INTERNSHIPS_URL
from app.normalize.adapters.simplify_internships import FEED_URL_2027 as SIMPLIFY_INTERNSHIPS_2027_URL
from app.normalize.adapters.simplify_new_grad import FEED_URL as SIMPLIFY_NEW_GRAD_URL
from app.normalize.adapters.vanshb03_new_grad import FEED_URL as VANSHB03_URL
from app.normalize.adapters.vanshb03_new_grad import FEED_URL_2027 as VANSHB03_2027_URL

DISCOVERY_FEED_URLS = (
    SIMPLIFY_INTERNSHIPS_URL,
    SIMPLIFY_INTERNSHIPS_2027_URL,
    SIMPLIFY_NEW_GRAD_URL,
    VANSHB03_URL,
    VANSHB03_2027_URL,
)

MAX_WORKDAY_SITES_PER_HOST = 8

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
    "ON", "QC", "BC", "AB", "MB", "SK", "NS", "NB", "PE", "NL", "NT", "NU", "YT",
}
_COUNTRY_TOKENS = {
    "switzerland", "belgium", "canada", "germany", "france", "ireland",
    "netherlands", "australia", "singapore", "japan", "brazil", "mexico",
    "sweden", "denmark", "italy", "spain", "poland", "austria", "norway",
    "finland", "portugal", "scotland", "england", "wales", "uk",
}
_LOCATION_MARKERS = (
    "united-states",
    "united-kingdom",
    "u-s-",
    "home-based",
    "remote---",
    "nationwide",
)


@dataclass(frozen=True)
class BoardCandidate:
    name: str
    career_url: str
    industry: str | None
    parsed: ParsedBoard
    listing_count: int = 1


def candidates_from_listings(items: list[dict]) -> list[BoardCandidate]:
    """Extract unique Greenhouse/Lever/Ashby/Workday boards from listing apply URLs."""
    grouped: dict[tuple[str, ...], _Group] = {}
    workday_by_host: dict[str, list[tuple[tuple[str, ...], ParsedBoard, str]]] = defaultdict(list)

    for item in items:
        if not isinstance(item, dict):
            continue
        apply_url = str(item.get("url") or "").strip()
        name = str(item.get("company_name") or "").strip()
        if not apply_url:
            continue
        try:
            parsed = parse_career_url(apply_url)
        except ValueError:
            continue
        if _skip_parsed(parsed):
            continue
        identity = board_identity(parsed)
        if parsed.ats == "workday":
            workday_by_host[parsed.host or ""].append((identity, parsed, name))
            continue
        _add_group(grouped, identity, parsed, name)

    for host, rows in workday_by_host.items():
        site_counts: Counter[str] = Counter()
        site_parsed: dict[str, tuple[tuple[str, ...], ParsedBoard, Counter[str]]] = {}
        for identity, parsed, name in rows:
            site_key = (parsed.site or "").lower()
            if looks_like_location_slug(parsed.site or ""):
                continue
            site_counts[site_key] += 1
            if site_key not in site_parsed:
                site_parsed[site_key] = (identity, parsed, Counter())
            if name:
                site_parsed[site_key][2][name] += 1
        for site_key, _count in site_counts.most_common(MAX_WORKDAY_SITES_PER_HOST):
            identity, parsed, names = site_parsed[site_key]
            best_name = names.most_common(1)[0][0] if names else (parsed.tenant or host)
            _add_group(grouped, identity, parsed, best_name, count=site_counts[site_key])

    return [_group_to_candidate(group) for group in grouped.values()]


def candidates_from_seed_file(path: Path) -> list[BoardCandidate]:
    raw = json.loads(path.read_text())
    entries = raw.get("companies", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError(f"{path} must be a JSON list or an object with companies[]")
    candidates: list[BoardCandidate] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("career_url") or entry.get("url") or "").strip()
        name = str(entry.get("name") or "").strip()
        industry = str(entry.get("industry") or "").strip() or None
        if not url:
            continue
        parsed = parse_career_url(url)
        candidates.append(
            BoardCandidate(
                name=name or _fallback_name(parsed),
                career_url=canonical_career_url(parsed),
                industry=industry,
                parsed=parsed,
            )
        )
    return candidates


def looks_like_location_slug(slug: str) -> bool:
    """True when a Workday path segment is a city/country, not a career-site slug."""
    if not slug:
        return True
    lowered = slug.lower()
    if any(marker in lowered for marker in _LOCATION_MARKERS):
        return True
    tokens = {part for part in lowered.replace("_", "-").split("-") if part}
    if tokens & _COUNTRY_TOKENS:
        return True
    parts = slug.split("-")
    if len(parts) >= 2 and parts[-1].upper() in _STATE_CODES and len(parts[-1]) == 2:
        return True
    return False


def _skip_parsed(parsed: ParsedBoard) -> bool:
    board = parsed.board or ""
    if parsed.ats in {"greenhouse", "lever", "ashby"} and _UUID_RE.match(board):
        return True
    if parsed.ats == "greenhouse" and board.lower() in {"embed", "job_board", "job_app"}:
        return True
    return False


@dataclass
class _Group:
    parsed: ParsedBoard
    names: Counter[str]
    count: int = 0


def _add_group(
    grouped: dict[tuple[str, ...], _Group],
    identity: tuple[str, ...],
    parsed: ParsedBoard,
    name: str,
    count: int = 1,
) -> None:
    group = grouped.get(identity)
    if group is None:
        group = _Group(parsed=parsed, names=Counter())
        grouped[identity] = group
    group.count += count
    if name:
        group.names[name] += count


def _group_to_candidate(group: _Group) -> BoardCandidate:
    name = group.names.most_common(1)[0][0] if group.names else _fallback_name(group.parsed)
    return BoardCandidate(
        name=name,
        career_url=canonical_career_url(group.parsed),
        industry=None,
        parsed=group.parsed,
        listing_count=group.count,
    )


def _fallback_name(parsed: ParsedBoard) -> str:
    host = urlparse(f"https://{parsed.host}").netloc if parsed.host else ""
    raw = parsed.board or parsed.tenant or host.split(".")[0] or parsed.ats
    cleaned = raw.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in cleaned.split()) or parsed.ats
