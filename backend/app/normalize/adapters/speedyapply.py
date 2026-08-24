"""Adapters for SpeedyApply college-job markdown tables (not listings.json)."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone

from app.normalize.adapters.base import FeedAdapter
from app.normalize.adapters.listings_json import build_job
from app.normalize.dates import parse_feed_datetime
from app.schemas.job import Job

SWE_MARKDOWN_URLS = (
    "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/README.md",
    "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/NEWGRAD_USA.md",
    "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/INTERN_INTL.md",
    "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/NEWGRAD_INTL.md",
)
AI_MARKDOWN_URLS = (
    "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/README.md",
    "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/NEWGRAD_USA.md",
    "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/INTERN_INTL.md",
    "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/NEWGRAD_INTL.md",
)

_HREF = re.compile(r'href="(https?://[^"]+)"', re.IGNORECASE)
_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_TAG = re.compile(r"<[^>]+>")
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}")


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _strip_cell(cell: str) -> str:
    without_tags = _TAG.sub("", html.unescape(cell))
    without_md, _ = _MD_LINK.subn(r"\1", without_tags)
    return re.sub(r"\s+", " ", without_md).strip()


def _hrefs(cell: str) -> list[str]:
    found = _HREF.findall(cell)
    found.extend(match.group(2) for match in _MD_LINK.finditer(cell))
    return found


def parse_speedyapply_markdown(
    text: str,
    *,
    feed_tag: str,
    seen_at: datetime | None = None,
) -> list[Job]:
    """Parse SpeedyApply GitHub markdown tables into Job objects."""
    seen_at = seen_at or datetime.now(timezone.utc)
    jobs: list[Job] = []
    seen_urls: set[str] = set()
    column_index: dict[str, int] | None = None

    for line in text.splitlines():
        if "|" not in line:
            column_index = None
            continue
        cells = _split_row(line)
        if not cells:
            continue
        if _SEPARATOR.match(cells[0] if cells else ""):
            continue

        header_names = [cell.lower() for cell in (_strip_cell(c) for c in cells)]
        if "company" in header_names and "position" in header_names:
            column_index = {name: idx for idx, name in enumerate(header_names)}
            continue
        if column_index is None:
            continue

        posting_idx = column_index.get("posting")
        company_idx = column_index.get("company")
        title_idx = column_index.get("position")
        location_idx = column_index.get("location")
        age_idx = column_index.get("age")
        if posting_idx is None or company_idx is None or title_idx is None:
            continue
        if max(posting_idx, company_idx, title_idx) >= len(cells):
            continue

        posting_cell = cells[posting_idx]
        apply_hrefs = [
            url
            for url in _hrefs(posting_cell)
            if "imgur.com" not in url and "github.com/user-attachments" not in url
        ]
        if not apply_hrefs:
            continue
        apply_url = html.unescape(apply_hrefs[0]).strip()
        if apply_url in seen_urls:
            continue
        seen_urls.add(apply_url)

        company = _strip_cell(cells[company_idx])
        title = _strip_cell(cells[title_idx])
        if not company or not title:
            continue

        location = "Unknown"
        if location_idx is not None and location_idx < len(cells):
            location = _strip_cell(cells[location_idx]) or "Unknown"
        age = ""
        if age_idx is not None and age_idx < len(cells):
            age = _strip_cell(cells[age_idx])

        source_job_id = hashlib.sha256(apply_url.encode()).hexdigest()[:32]
        jobs.append(
            build_job(
                company=company,
                title=title,
                locations=[location],
                apply_url=apply_url,
                date_posted=parse_feed_datetime(age, now=seen_at),
                feed_tag=feed_tag,
                source_job_id=source_job_id,
                seen_at=seen_at,
                posting_active=True,
            )
        )

    return jobs


class SpeedyApplyAdapter(FeedAdapter):
    """Fetch one or more SpeedyApply markdown files and parse job tables."""

    def __init__(self, source_name: str, urls: tuple[str, ...]) -> None:
        self.source_name = source_name
        self.feed_url = urls[0]
        self.urls = urls

    def normalize(self, raw: list | dict) -> list[Job]:
        raise TypeError("SpeedyApplyAdapter reads markdown via fetch_and_normalize")

    def fetch_and_normalize(self, fetch_json, fetch_text=None) -> list[Job]:
        if fetch_text is None:
            raise TypeError("SpeedyApplyAdapter requires fetch_text")
        now = datetime.now(timezone.utc)
        jobs: list[Job] = []
        errors: list[str] = []
        for url in self.urls:
            try:
                text = fetch_text(url)
            except Exception as exc:  # isolated per file; other files still ingest
                errors.append(f"{url}: {exc}")
                continue
            jobs.extend(parse_speedyapply_markdown(text, feed_tag=self.source_name, seen_at=now))
        if errors and not jobs:
            raise RuntimeError("; ".join(errors))
        return jobs
