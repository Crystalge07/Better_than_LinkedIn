"""Pure dedupe: exact fingerprint match + URL conflict guard."""

from __future__ import annotations

from collections import Counter

from app.normalize.apply_url import (
    apply_url_netloc,
    pick_preferred_apply_url,
    score_apply_url,
    urls_conflict,
)
from app.schemas.job import Job


def merge_jobs(jobs: list[Job]) -> list[Job]:
    """Dedupe jobs by fingerprint, splitting on conflicting apply URLs."""
    if not jobs:
        return []

    by_fingerprint: dict[str, list[Job]] = {}
    for job in jobs:
        by_fingerprint.setdefault(job.fingerprint, []).append(job)

    merged: list[Job] = []
    for fingerprint, group in by_fingerprint.items():
        for cluster in _cluster_by_url_compatibility(group):
            merged.append(merge_job_group(cluster))
    return sorted(merged, key=_job_sort_key)


def merge_job_group(jobs: list[Job]) -> Job:
    """Merge jobs that share a fingerprint and compatible apply URLs."""
    if not jobs:
        raise ValueError("merge_job_group requires at least one job")
    if len(jobs) == 1:
        return jobs[0]

    winner = _pick_display_job(jobs)
    preferred_url = pick_preferred_apply_url([job.apply_url for job in jobs])
    sources: list[str] = []
    for job in jobs:
        for source in job.sources:
            if source not in sources:
                sources.append(source)

    return winner.model_copy(
        update={
            "apply_url": preferred_url,
            "sources": sources,
            "date_posted": min(job.date_posted for job in jobs),
            "posting_active": any(job.posting_active for job in jobs),
            "fingerprint": jobs[0].fingerprint,
        }
    )


def _cluster_by_url_compatibility(jobs: list[Job]) -> list[list[Job]]:
    netloc_counts = Counter(apply_url_netloc(job.apply_url) for job in jobs)
    clusters: list[list[Job]] = []

    for job in jobs:
        placed = False
        for cluster in clusters:
            if all(
                not urls_conflict(
                    job.apply_url,
                    other.apply_url,
                    netloc_counts=netloc_counts,
                )
                for other in cluster
            ):
                cluster.append(job)
                placed = True
                break
        if not placed:
            clusters.append([job])

    return clusters


def _pick_display_job(jobs: list[Job]) -> Job:
    preferred_url = pick_preferred_apply_url([job.apply_url for job in jobs])
    for job in jobs:
        if job.apply_url == preferred_url:
            return job
    return max(jobs, key=lambda job: (score_apply_url(job.apply_url), job.source))


def _job_sort_key(job: Job) -> tuple[str, str, str]:
    return (job.fingerprint, job.apply_url, job.source_job_id)
