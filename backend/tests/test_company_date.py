from datetime import datetime, timezone

from app.ats.company_date import overlay_company_posted_dates
from app.ats.job_url import parse_ats_job_ref, posting_identity, workday_posting_key
from app.schemas.job import Job

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)
ATS_POSTED = datetime(2025, 1, 15, tzinfo=timezone.utc)
TESLA_POSTED = datetime(2026, 5, 6, tzinfo=timezone.utc)
WORKDAY_POSTED = datetime(2026, 4, 1, tzinfo=timezone.utc)


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


def test_overlay_copies_workday_date_from_company_board_sibling():
    feed = _job(
        company="NVIDIA",
        title="Software Engineering Intern",
        apply_url="https://nvidia.wd5.myworkdayjobs.com/job/JR2023492",
        date_posted=NOW,
        source="simplify_internships",
    )
    board = _job(
        company="NVIDIA",
        title="Software Engineering Intern",
        apply_url=(
            "https://nvidia.wd5.myworkdayjobs.com/en-US/"
            "NVIDIAExternalCareerSite/job/Santa-Clara/Intern_JR2023492"
        ),
        date_posted=WORKDAY_POSTED,
        source="workday:nvidia",
    )
    out = overlay_company_posted_dates([feed, board], fetch_json=lambda _url: {})
    by_source = {job.source: job for job in out}
    assert by_source["simplify_internships"].date_posted == WORKDAY_POSTED
    assert by_source["simplify_internships"].apply_url == board.apply_url
    assert by_source["workday:nvidia"].date_posted == WORKDAY_POSTED


def test_overlay_uses_tesla_careers_board_date_not_feed_date():
    job = _job(
        company="Tesla",
        title="Software Engineer Intern",
        apply_url="https://www.tesla.com/careers/search/job/software-engineer-intern-281271",
        date_posted=NOW,
        source="simplify_internships",
    )

    def fetch_json(url: str):
        assert "tesla.com" in url
        return {
            "listings": [
                {"id": "281271", "t": "Software Engineer Intern", "datePosted": "2026-05-06T00:00:00Z"}
            ]
        }

    out = overlay_company_posted_dates([job], fetch_json=fetch_json)
    assert out[0].date_posted == TESLA_POSTED


def test_workday_and_tesla_posting_identity():
    assert workday_posting_key(
        "https://nvidia.wd5.myworkdayjobs.com/job/JR2023492"
    ) == ("nvidia.wd5.myworkdayjobs.com", "jr2023492")
    assert posting_identity(
        "https://www.tesla.com/careers/search/job/281271"
    ) == ("tesla", "281271")


def test_parse_greenhouse_embed_on_company_career_page():
    ref = parse_ats_job_ref("https://stripe.com/jobs/search?gh_jid=7532733")
    assert ref is not None
    assert ref.ats == "greenhouse"
    assert ref.job_id == "7532733"


def test_overlay_rewrites_hosted_board_to_company_career_url():
    job = _job(apply_url="https://job-boards.greenhouse.io/stripe/jobs/7532733")

    def fetch_json(url: str):
        assert "stripe" in url
        return {
            "jobs": [
                {
                    "id": 7532733,
                    "first_published": "2025-01-15T00:00:00Z",
                    "absolute_url": "https://stripe.com/jobs/search?gh_jid=7532733",
                }
            ]
        }

    out = overlay_company_posted_dates([job], fetch_json=fetch_json)
    assert out[0].apply_url == "https://stripe.com/jobs/search?gh_jid=7532733"
    assert out[0].date_posted == ATS_POSTED


def test_overlay_dates_company_career_url_via_shared_job_id():
    hosted = _job(apply_url="https://job-boards.greenhouse.io/psiquantum/jobs/7695577003")
    career = _job(
        apply_url="https://www.psiquantum.com/apply?gh_jid=7695577003",
        source="simplify_internships",
        fingerprint="fp-psi",
    )

    def fetch_json(url: str):
        return {
            "jobs": [
                {
                    "id": 7695577003,
                    "first_published": "2025-01-15T00:00:00Z",
                    "absolute_url": "https://www.psiquantum.com/apply?gh_jid=7695577003",
                }
            ]
        }

    out = overlay_company_posted_dates([hosted, career], fetch_json=fetch_json)
    assert all(job.date_posted == ATS_POSTED for job in out)
    assert all("psiquantum.com" in job.apply_url for job in out)
