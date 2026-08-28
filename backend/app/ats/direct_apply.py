"""Rewrite aggregator apply links to the company career posting.

WarpJobs / Simplify.jobs (and similar boards) host a copy of the listing and
point Apply at themselves. Prefer the employer's own posting (Tesla careers,
Workday, Greenhouse, …) encoded in that page's JSON-LD or apply href.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin, urlparse

from app.ats.job_url import (
    canonical_ats_apply_url,
    canonical_company_apply_url,
    parse_ats_identifier,
    parse_ats_job_ref,
)
from app.normalize.apply_url import (
    is_aggregator_apply_url,
    is_company_career_url,
    is_hosted_ats_board_url,
    looks_like_job_posting_url,
    pick_preferred_apply_url,
    strip_tracking_query,
)
from app.schemas.job import Job

logger = logging.getLogger(__name__)

_JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_HREF = re.compile(r"""href\s*=\s*["']([^"'#]+)["']""", re.IGNORECASE)
_ABS_HTTP = re.compile(r"https://[^\s\"'<>\\]+", re.IGNORECASE)


def company_apply_url_from_html(html: str, *, page_url: str = "") -> str | None:
    """Return the company career/ATS posting encoded on an aggregator page."""
    candidates: list[str] = []
    for raw in _JSON_LD.findall(html):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates.extend(_candidates_from_json_ld(payload))

    for href in _HREF.findall(html):
        candidates.append(href)
    candidates.extend(_ABS_HTTP.findall(html))

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        url = _clean_url(raw, page_url)
        if not url or url in seen:
            continue
        if is_aggregator_apply_url(url) or not looks_like_job_posting_url(url):
            continue
        seen.add(url)
        cleaned.append(url)
    if not cleaned:
        return None
    return pick_preferred_apply_url(cleaned)


def resolve_company_apply_urls(jobs: list[Job], *, fetch_text) -> list[Job]:
    """Replace aggregator apply URLs with the company career posting when possible."""
    cache: dict[str, str | None] = {}
    updated: list[Job] = []
    resolved = 0
    for job in jobs:
        apply_url = job.apply_url
        if is_aggregator_apply_url(apply_url):
            if apply_url not in cache:
                cache[apply_url] = _resolve_one(apply_url, fetch_text)
            direct = cache[apply_url]
            if direct:
                resolved += 1
                apply_url = direct
        canonical = canonical_company_apply_url(apply_url, job.title)
        if canonical != job.apply_url:
            updated.append(job.model_copy(update={"apply_url": canonical}))
        else:
            updated.append(job)
    if resolved:
        logger.info("Resolved %d aggregator apply URLs to company postings", resolved)
    return updated


def _resolve_one(url: str, fetch_text) -> str | None:
    try:
        html = fetch_text(url)
    except Exception:
        logger.exception("Failed to fetch aggregator listing %s", url)
        return None
    return company_apply_url_from_html(html, page_url=url)


def _candidates_from_json_ld(payload: object) -> list[str]:
    if isinstance(payload, list):
        found: list[str] = []
        for item in payload:
            found.extend(_candidates_from_json_ld(item))
        return found
    if not isinstance(payload, dict):
        return []
    graph = payload.get("@graph")
    if graph is not None:
        return _candidates_from_json_ld(graph)
    if payload.get("@type") != "JobPosting":
        return []

    candidates: list[str] = []
    for value in _identifier_values(payload.get("identifier")):
        ref = parse_ats_identifier(str(value))
        if ref is not None:
            candidates.append(canonical_ats_apply_url(ref))
    for key in ("sameAs", "url", "applicationUrl"):
        candidate = payload.get(key)
        if isinstance(candidate, str):
            candidates.append(candidate)
        elif isinstance(candidate, list):
            candidates.extend(str(item) for item in candidate if item)
    return candidates


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


def _clean_url(raw: str, page_url: str) -> str | None:
    text = raw.strip().rstrip("\\").rstrip("'\"").replace("\\u003c", "").replace("\\/", "/")
    if not text or text.startswith("data:") or text.startswith("javascript:"):
        return None
    if page_url and not urlparse(text).scheme:
        text = urljoin(page_url, text)
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if is_company_career_url(text) or (
        looks_like_job_posting_url(text)
        and not is_hosted_ats_board_url(text)
        and not is_aggregator_apply_url(text)
    ):
        return strip_tracking_query(text)
    ref = parse_ats_job_ref(text)
    if ref is not None and ref.board:
        return canonical_ats_apply_url(ref)
    return strip_tracking_query(text)
