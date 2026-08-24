import json

import httpx

from app.ats.ashby import ashby_jobs_url
from app.ats.career_url import parse_career_url
from app.ats.companies_file import merge_company_rows
from app.ats.discover import candidates_from_listings, looks_like_location_slug
from app.ats.probe import probe_board


def test_location_slug_detects_city_state_not_career_site():
    assert looks_like_location_slug("Buffalo-NY")
    assert looks_like_location_slug("Milwaukee-Wisconsin-United-States-of-America")
    assert looks_like_location_slug("Toronto-Ontario-Canada")
    assert not looks_like_location_slug("CaterpillarCareers")
    assert not looks_like_location_slug("1000")
    assert not looks_like_location_slug("External")


def test_discover_listings_keeps_unique_boards_and_drops_locations():
    items = [
        {
            "company_name": "Stripe",
            "url": "https://job-boards.greenhouse.io/stripe/jobs/111",
        },
        {
            "company_name": "Stripe",
            "url": "https://job-boards.greenhouse.io/stripe/jobs/222",
        },
        {
            "company_name": "Procter & Gamble",
            "url": "https://pg.wd5.myworkdayjobs.com/1000/job/CINCINNATI/Intern_R1",
        },
        {
            "company_name": "Johnson Controls",
            "url": "https://jci.wd5.myworkdayjobs.com/en-US/Milwaukee-Wisconsin-United-States-of-America/job/Intern_R2",
        },
        {
            "company_name": "LinkedIn",
            "url": "https://www.linkedin.com/jobs/view/123",
        },
    ]
    candidates = candidates_from_listings(items)
    urls = {candidate.career_url for candidate in candidates}
    assert "https://job-boards.greenhouse.io/stripe" in urls
    assert "https://pg.wd5.myworkdayjobs.com/1000" in urls
    assert not any("Milwaukee" in url for url in urls)
    stripe = next(c for c in candidates if c.parsed.board == "stripe")
    assert stripe.listing_count == 2


def test_probe_greenhouse_ok_with_name_hint():
    parsed = parse_career_url("https://job-boards.greenhouse.io/stripe")
    calls: list[str] = []

    def fetch_json(url: str):
        calls.append(url)
        return {"jobs": []}

    result = probe_board(
        parsed,
        fetch_json=fetch_json,
        post_json=lambda *args, **kwargs: {},
        name_hint="Stripe",
    )
    assert result.ok
    assert result.name == "Stripe"
    assert calls == ["https://boards-api.greenhouse.io/v1/boards/stripe/jobs"]


def test_probe_workday_retries_empty_search_on_422():
    parsed = parse_career_url("https://walmart.wd5.myworkdayjobs.com/WalmartExternal")
    searches: list[str] = []

    def post_json(url, payload, extra_headers=None):
        searches.append(payload["searchText"])
        if payload["searchText"] == "":
            request = httpx.Request("POST", url)
            response = httpx.Response(422, request=request)
            raise httpx.HTTPStatusError("422", request=request, response=response)
        return {"jobPostings": []}

    result = probe_board(parsed, fetch_json=lambda url: {}, post_json=post_json)
    assert result.ok
    assert searches == ["", "intern"]


def test_probe_workday_requires_job_postings_key():
    parsed = parse_career_url("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")

    def post_json(url, payload, extra_headers=None):
        assert "wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs" in url
        return {"jobPostings": []}

    result = probe_board(parsed, fetch_json=lambda url: {}, post_json=post_json)
    assert result.ok


def test_merge_fills_industry_without_duplicating_board():
    existing = [{"name": "Stripe", "ats": "greenhouse", "board": "stripe"}]
    incoming = [
        {
            "name": "Stripe",
            "industry": "fintech",
            "ats": "greenhouse",
            "board": "stripe",
            "career_url": "https://job-boards.greenhouse.io/stripe",
        }
    ]
    merged = merge_company_rows(existing, incoming)
    assert len(merged) == 1
    assert merged[0]["industry"] == "fintech"
    assert merged[0]["career_url"] == "https://job-boards.greenhouse.io/stripe"


def test_ashby_url_quotes_spaces():
    assert "Citizen%20Health" in ashby_jobs_url("Citizen Health")


def test_seed_file_parses(tmp_path):
    from app.ats.discover import candidates_from_seed_file

    path = tmp_path / "seeds.json"
    path.write_text(
        json.dumps(
            {
                "companies": [
                    {
                        "name": "Spotify",
                        "industry": "media",
                        "career_url": "https://jobs.lever.co/spotify",
                    }
                ]
            }
        )
    )
    candidates = candidates_from_seed_file(path)
    assert len(candidates) == 1
    assert candidates[0].parsed.ats == "lever"
    assert candidates[0].industry == "media"
