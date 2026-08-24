"""Rewrite aggregator apply links to the company ATS posting.

WarpJobs / AI Infra Jobs (and similar boards) host a copy of the listing and
point Apply at themselves. Their JobPosting JSON-LD includes an ATS identifier
(`gh-togetherai-5214645007`) and/or the real Greenhouse/Lever/Ashby URL.
We read that structured data from the aggregator page — not company career HTML.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

from app.ats.job_url import (
    canonical_ats_apply_url,
    parse_ats_identifier,
    parse_ats_job_ref,
)
from app.schemas.job import Job

logger = logging.getLogger(__name__)

_JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_ATS_HREF = re.compile(
    r"https://(?:job-boards|boards)\.greenhouse\.io/[^\s\"'<>\\]+"
    r"|https://jobs\.lever\.co/[^\s\"'<>\\]+"
    r"|https://jobs\.ashbyhq\.com/[^\s\"'<>\\]+"
    r"|https://[a-z0-9.-]+\.myworkdayjobs\.com/[^\s\"'<>\\]+",
    re.IGNORECASE,
)


def is_aggregator_apply_url(url: str) -> bool:
    host = (urlparse(url.strip()).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host == "warpjobs.com"


def company_apply_url_from_html(html: str) -> str | None:
    """Return the company ATS apply URL encoded in aggregator JobPosting JSON-LD."""
    for raw in _JSON_LD.findall(html):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        found = _from_json_ld(payload)
        if found:
            return found

    match = _ATS_HREF.search(html)
    if not match:
        return None
    href = match.group(0).rstrip("\\").rstrip("'\"")
    ref = parse_ats_job_ref(href)
    if ref is not None:
        return canonical_ats_apply_url(ref)
    return href.split("?")[0]


def resolve_company_apply_urls(jobs: list[Job], *, fetch_text) -> list[Job]:
    """Replace aggregator apply URLs with the company ATS posting when possible."""
    cache: dict[str, str | None] = {}
    updated: list[Job] = []
    resolved = 0
    for job in jobs:
        if not is_aggregator_apply_url(job.apply_url):
            updated.append(job)
            continue
        if job.apply_url not in cache:
            cache[job.apply_url] = _resolve_one(job.apply_url, fetch_text)
        direct = cache[job.apply_url]
        if not direct:
            updated.append(job)
            continue
        resolved += 1
        updated.append(job.model_copy(update={"apply_url": direct}))
    if resolved:
        logger.info("Resolved %d aggregator apply URLs to company ATS postings", resolved)
    return updated


def _resolve_one(url: str, fetch_text) -> str | None:
    try:
        html = fetch_text(url)
    except Exception:
        logger.exception("Failed to fetch aggregator listing %s", url)
        return None
    return company_apply_url_from_html(html)


def _from_json_ld(payload: object) -> str | None:
    if isinstance(payload, list):
        for item in payload:
            found = _from_json_ld(item)
            if found:
                return found
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("@type") == "JobPosting":
        identifier = payload.get("identifier")
        values = _identifier_values(identifier)
        for value in values:
            ref = parse_ats_identifier(str(value))
            if ref is not None:
                return canonical_ats_apply_url(ref)
        for key in ("sameAs", "url"):
            candidate = payload.get(key)
            if isinstance(candidate, str):
                ref = parse_ats_job_ref(candidate)
                if ref is not None:
                    return canonical_ats_apply_url(ref)
        return None
    graph = payload.get("@graph")
    if graph is not None:
        return _from_json_ld(graph)
    return None


def _identifier_values(identifier: object) -> list[str]:
    if isinstance(identifier, str):
        return [identifier]
    if isinstance(identifier, dict):
        value = identifier.get("value")
        return [str(value)] if value else []
    if isinstance(identifier, list):
        values: list[str] = []
        for item in identifier:
            values.extend(_identifier_values(item))
        return values
    return []
