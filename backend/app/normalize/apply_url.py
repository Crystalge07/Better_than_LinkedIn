"""Shared apply_url parsing for dedupe conflict checks and tie-break scoring."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Prefer the employer's own career posting over hosted ATS boards, then aggregators.
_APPLY_URL_SCORES: tuple[tuple[str, int], ...] = (
    ("myworkdayjobs.com", 100),
    ("myworkdaysite.com", 100),
    ("greenhouse.io", 95),
    ("lever.co", 95),
    ("ashbyhq.com", 90),
    ("smartrecruiters.com", 85),
    ("careers.microsoft.com", 85),
    ("jobs.lever.co", 95),
    ("icims.com", 80),
    ("taleo.net", 80),
    ("simplify.jobs", 10),
    ("jobright.ai", 10),
    ("zapply", 10),
    ("warpjobs.com", 15),
    ("careerkit.me", 10),
    ("speedyapply.com", 10),
)

_HOSTED_ATS_HOSTS = frozenset(
    {
        "job-boards.greenhouse.io",
        "job-boards.eu.greenhouse.io",
        "boards.greenhouse.io",
        "boards.eu.greenhouse.io",
        "jobs.lever.co",
        "api.lever.co",
        "jobs.ashbyhq.com",
        "api.ashbyhq.com",
    }
)

_KEEP_QUERY_KEYS = frozenset({"gh_jid", "for", "token", "t"})

AGGREGATOR_HOSTS = frozenset(
    {
        "warpjobs.com",
        "simplify.jobs",
        "jobright.ai",
        "zapplyjobs.com",
        "careerkit.me",
        "speedyapply.com",
    }
)

_JOB_POSTING_PATH = re.compile(
    r"/jobs?(?:/|$)|/careers?(?:/|$)|/posting|/requisition|/apply(?:/|$)|/join-us|/open-positions|/details/",
    re.IGNORECASE,
)


def apply_host(url: str) -> str:
    host = (urlparse(url.strip()).hostname or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def is_aggregator_apply_url(url: str) -> bool:
    return apply_host(url) in AGGREGATOR_HOSTS


def looks_like_job_posting_url(url: str) -> bool:
    """True when the path looks like a specific posting, not a homepage."""
    parsed = urlparse(url.strip())
    if not parsed.hostname:
        return False
    path = parsed.path or "/"
    query = (parsed.query or "").lower()
    haystack = f"{path}?{query}"
    if "gh_jid=" in query or "token=" in query:
        return True
    return bool(_JOB_POSTING_PATH.search(haystack))


def is_hosted_ats_board_url(url: str) -> bool:
    """Greenhouse / Lever / Ashby vendor hosts — replace when a company career URL exists."""
    host = apply_host(url)
    if host in _HOSTED_ATS_HOSTS:
        return True
    return "greenhouse.io" in host


def is_company_career_url(url: str) -> bool:
    """Employer-owned career posting (Tesla, Stripe, Apple, Workday, …)."""
    if is_aggregator_apply_url(url) or is_hosted_ats_board_url(url):
        return False
    return looks_like_job_posting_url(url)


def strip_tracking_query(url: str) -> str:
    parsed = urlparse(url.strip())
    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() in _KEEP_QUERY_KEYS
    ]
    query = urlencode(kept)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def apply_url_netloc(url: str) -> str:
    return urlparse(url.strip()).netloc.lower()


def apply_url_path(url: str) -> str:
    return urlparse(url.strip()).path.rstrip("/").lower()


def score_apply_url(url: str) -> int:
    """Higher score = more direct apply link."""
    lowered = url.strip().lower()
    score = 0
    if is_company_career_url(url):
        score = 120
    for fragment, points in _APPLY_URL_SCORES:
        if fragment in lowered:
            score = max(score, points)
    if lowered.startswith("https://") and "utm_" not in lowered:
        score += 1
    return score


def urls_conflict(url_a: str, url_b: str) -> bool:
    """True when two apply URLs must not be merged.

    Same netloc + same path → compatible.
    Same netloc + different path → conflict.
    Different netloc → always conflict (no cross-host syndication merge).
    """
    if not url_a.strip() or not url_b.strip():
        return False
    if url_a.strip() == url_b.strip():
        return False

    netloc_a = apply_url_netloc(url_a)
    netloc_b = apply_url_netloc(url_b)
    if netloc_a != netloc_b:
        return True

    return apply_url_path(url_a) != apply_url_path(url_b)


def pick_preferred_apply_url(urls: list[str]) -> str:
    return max(
        urls,
        key=lambda url: (
            score_apply_url(url),
            len(apply_url_path(url)),
            -len(urlparse(url).query),
            url,
        ),
    )
