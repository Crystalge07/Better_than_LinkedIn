from datetime import datetime, timezone

from app.normalize.adapters.heynish_dach import map_heynish_role
from app.normalize.adapters.warpjobs import map_warp_job


NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)


def test_warp_job_mapping():
    job = map_warp_job(
        {
            "title": "Staff Software Engineer, Inference",
            "company": "Together AI",
            "locations": ["London", "San Francisco"],
            "region": "UK",
            "posted": "2d",
            "url": "https://warpjobs.com/jobs/together-ai-staff-software-engineer-645007/",
        },
        feed_tag="warpjobs",
        seen_at=NOW,
    )
    assert job is not None
    assert job.company == "Together AI"
    assert "London" in job.locations
    assert job.apply_url.startswith("https://warpjobs.com/")
    assert job.source == "warpjobs"


def test_heynish_prefers_raw_ats_url():
    job = map_heynish_role(
        {
            "company": "1KOMMA5°",
            "title": "Graduate Program - Sales",
            "city": "Berlin",
            "location": "Berlin",
            "posted": "2025-09-22T14:48:49+00:00",
            "raw_url": "https://1komma5grad.jobs.personio.de/job/2354909",
            "careerkit_apply_url": "https://careerkit.me/api/apply?src=github-dach",
        },
        feed_tag="heynish_dach",
        seen_at=NOW,
    )
    assert job is not None
    assert job.apply_url == "https://1komma5grad.jobs.personio.de/job/2354909"
    assert job.locations == ["Berlin"]
    assert job.date_posted.year == 2025
