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
    ("warpjobs.com", 15),
    ("careerkit.me", 10),
    ("speedyapply.com", 10),
)


def apply_url_netloc(url: str) -> str:
    return urlparse(url.strip()).netloc.lower()


def apply_url_path(url: str) -> str:
    return urlparse(url.strip()).path.rstrip("/").lower()


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
    return max(urls, key=lambda url: (score_apply_url(url), -len(url), url))
