from datetime import datetime, timezone

from app.ats.ashby import map_ashby_jobs
from app.ats.greenhouse import map_greenhouse_jobs
from app.ats.lever import map_lever_jobs
from app.ats.career_url import parse_career_url
from app.ats.workday import map_workday_page

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)


def test_greenhouse_keeps_intern_drops_senior():
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "Software Engineer Intern",
                "absolute_url": "https://example.com/intern",
                "location": {"name": "NYC"},
                "first_published": "2026-08-01T00:00:00Z",
            },
            {
                "id": 2,
                "title": "Staff Software Engineer",
                "absolute_url": "https://example.com/staff",
                "location": {"name": "NYC"},
                "first_published": "2026-08-01T00:00:00Z",
            },
        ]
    }
    jobs = map_greenhouse_jobs(payload, company="Stripe", source="greenhouse:stripe", seen_at=NOW)
    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer Intern"
    assert jobs[0].source_job_id == "1"


def test_lever_new_grad():
    payload = [
        {
            "id": "abc",
            "text": "New Grad Product Manager",
            "hostedUrl": "https://jobs.lever.co/spotify/abc",
            "createdAt": 1750000000000,
            "categories": {"location": "Stockholm"},
        }
    ]
    jobs = map_lever_jobs(payload, company="Spotify", source="lever:spotify", seen_at=NOW)
    assert len(jobs) == 1
    assert jobs[0].locations == ["Stockholm"]


def test_ashby_filters_unlisted_and_senior():
    payload = {
        "jobs": [
            {
                "id": "a1",
                "title": "Research Intern",
                "jobUrl": "https://jobs.ashbyhq.com/openai/a1",
                "location": "San Francisco",
                "publishedAt": "2026-08-01T00:00:00Z",
                "isListed": True,
            },
            {
                "id": "a2",
                "title": "Research Intern Hidden",
                "jobUrl": "https://jobs.ashbyhq.com/openai/a2",
                "location": "San Francisco",
                "isListed": False,
            },
        ]
    }
    jobs = map_ashby_jobs(payload, company="OpenAI", source="ashby:openai", seen_at=NOW)
    assert [job.source_job_id for job in jobs] == ["a1"]


def test_workday_page_maps_apply_url():
    board = parse_career_url("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")
    payload = {
        "jobPostings": [
            {
                "title": "Software Intern",
                "externalPath": "/job/US-CA-Santa-Clara/Software-Intern_JR1",
                "locationsText": "Santa Clara, CA",
                "postedOn": "Posted 4 Days Ago",
                "bulletFields": ["JR1"],
            }
        ]
    }
    jobs = map_workday_page(
        payload,
        company="NVIDIA",
        source="workday:NVIDIAExternalCareerSite",
        board=board,
        seen_at=NOW,
    )
    assert len(jobs) == 1
    assert jobs[0].source_job_id == "JR1"
    assert "NVIDIAExternalCareerSite" in jobs[0].apply_url
    assert jobs[0].apply_url.endswith("/job/US-CA-Santa-Clara/Software-Intern_JR1")
