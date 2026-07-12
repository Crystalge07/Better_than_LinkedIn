"""Shared apply_url parsing for dedupe conflict checks and tie-break scoring."""

from __future__ import annotations

from urllib.parse import urlparse

# Prefer direct employer / ATS URLs over aggregators and tracking redirects.
_APPLY_URL_SCORES: tuple[tuple[str, int], ...] = (
    ("myworkdayjobs.com", 100),
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
)


def apply_url_netloc(url: str) -> str:
    return urlparse(url.strip()).netloc.lower()


def apply_url_path(url: str) -> str:
    return urlparse(url.strip()).path.rstrip("/").lower()


def apply_url_registrable_domain(url: str) -> str:
    netloc = apply_url_netloc(url)
    if netloc.startswith("www."):
        netloc = netloc[4:]
    parts = netloc.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return netloc


def score_apply_url(url: str) -> int:
    """Higher score = more direct apply link."""
    lowered = url.strip().lower()
    score = 0
    for fragment, points in _APPLY_URL_SCORES:
        if fragment in lowered:
            score = max(score, points)
    if lowered.startswith("https://") and "utm_" not in lowered:
        score += 1
    return score


def urls_conflict(url_a: str, url_b: str, *, netloc_counts: dict[str, int] | None = None) -> bool:
    """True when two direct apply URLs must not be merged."""
    if not url_a.strip() or not url_b.strip():
        return False
    if url_a.strip() == url_b.strip():
        return False

    netloc_a = apply_url_netloc(url_a)
    netloc_b = apply_url_netloc(url_b)
    path_a = apply_url_path(url_a)
    path_b = apply_url_path(url_b)

    if netloc_a == netloc_b:
        return path_a != path_b

    domain_a = apply_url_registrable_domain(url_a)
    domain_b = apply_url_registrable_domain(url_b)
    if domain_a != domain_b:
        return True

    # Same employer domain on different hosts (e.g. apply.careers.* vs jobs.careers.*).
    # Allow syndication only when each host appears once in the fingerprint group.
    if netloc_counts is not None:
        if netloc_counts.get(netloc_a, 0) > 1 or netloc_counts.get(netloc_b, 0) > 1:
            return True
        return False

    return path_a != path_b


def pick_preferred_apply_url(urls: list[str]) -> str:
    return max(urls, key=lambda url: (score_apply_url(url), -len(url), url))
