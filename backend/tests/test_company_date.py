from datetime import datetime, timezone

from app.ats.company_date import overlay_company_posted_dates
from app.ats.job_url import parse_ats_job_ref
from app.schemas.job import Job

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)
ATS_POSTED = datetime(2025, 1, 15, tzinfo=timezone.utc)


def _job(**overrides) -> Job:
    data = {
        "company": "Together AI",
        "title": "Staff Software Engineer",
        "locations": ["Remote"],
        "apply_url": "https://job-boards.greenhouse.io/togetherai/jobs/5214645007",
        "date_posted": NOW,
        "source": "warpjobs",
        "source_job_id": "abc",
        "sources": ["warpjobs"],
        "first_seen": NOW,
        "last_seen": NOW,
        "active": True,
        "posting_active": True,
        "fingerprint": "fp",
    }
    data.update(overrides)
    return Job(**data)


def test_parse_greenhouse_job_url():
    ref = parse_ats_job_ref(
        "https://job-boards.greenhouse.io/togetherai/jobs/5214645007"
    )
    assert ref is not None
    assert ref.ats == "greenhouse"
    assert ref.board == "togetherai"
    assert ref.job_id == "5214645007"


def test_parse_ashby_and_lever_job_urls():
    ashby = parse_ats_job_ref(
        "https://jobs.ashbyhq.com/etched/b09ced5f-c81a-4fbe-a85e-ed743c991e21"
    )
    assert ashby is not None and ashby.ats == "ashby" and ashby.board == "etched"
    lever = parse_ats_job_ref("https://jobs.lever.co/netflix/abcd-1234/apply")
    assert lever is not None and lever.ats == "lever" and lever.job_id == "abcd-1234"


def test_warpjobs_url_is_not_an_ats_posting():
    assert parse_ats_job_ref("https://warpjobs.com/jobs/together-ai-role-645007/") is None


def test_overlay_uses_greenhouse_first_published_not_feed_date():
    job = _job()

    def fetch_json(url: str):
        assert "togetherai" in url
        return {
            "jobs": [
                {
                    "id": 5214645007,
                    "first_published": "2025-01-15T00:00:00Z",
                    "updated_at": "2026-08-20T00:00:00Z",
                }
            ]
        }

    out = overlay_company_posted_dates([job], fetch_json=fetch_json)
    assert out[0].date_posted == ATS_POSTED


def test_overlay_skips_direct_company_board_sources():
    job = _job(source="greenhouse:togetherai")
    calls: list[str] = []

    def fetch_json(url: str):
        calls.append(url)
        return {"jobs": []}

    out = overlay_company_posted_dates([job], fetch_json=fetch_json)
    assert calls == []
    assert out[0].date_posted == NOW
