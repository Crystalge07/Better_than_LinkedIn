from datetime import datetime, timezone

from app.ats.direct_apply import (
    company_apply_url_from_html,
    is_aggregator_apply_url,
    resolve_company_apply_urls,
)
from app.ats.job_url import canonical_tesla_apply_url, parse_ats_identifier, tesla_job_id
from app.schemas.job import Job

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)

_WARPJOBS_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org/","@type":"JobPosting","title":"Staff Software Engineer",
 "identifier":{"@type":"PropertyValue","name":"Together AI","value":"gh-togetherai-5214645007"},
 "url":"https://warpjobs.com/jobs/together-ai-staff-software-engineer-645007/"}
</script>
</head>
<body>
<a href="https://job-boards.greenhouse.io/togetherai/jobs/5214645007">Apply</a>
</body></html>
"""

_COMPANY_CAREER_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org/","@type":"JobPosting","title":"Software Engineer",
 "identifier":{"@type":"PropertyValue","name":"Stripe","value":"gh-stripe-7532733"},
 "url":"https://warpjobs.com/jobs/stripe-software-engineer-1/"}
</script>
</head>
<body>
<a href="https://stripe.com/jobs/search?gh_jid=7532733">Apply at Stripe</a>
<a href="https://job-boards.greenhouse.io/stripe/jobs/7532733">Greenhouse</a>
</body></html>
"""

_TESLA_AGGREGATOR_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org/","@type":"JobPosting","title":"Software Engineer Intern",
 "identifier":{"@type":"PropertyValue","name":"Tesla","value":"gh-tesla-999"},
 "url":"https://warpjobs.com/jobs/tesla-software-engineer-intern-1/"}
</script>
</head>
<body>
<a href="https://www.tesla.com/careers/search/job/281271">Apply on Tesla</a>
<a href="https://job-boards.greenhouse.io/tesla/jobs/999">Greenhouse copy</a>
</body></html>
"""


def _job(**overrides) -> Job:
    data = {
        "company": "Together AI",
        "title": "Staff Software Engineer",
        "locations": ["Remote"],
        "apply_url": "https://warpjobs.com/jobs/together-ai-staff-software-engineer-645007/",
        "date_posted": NOW,
        "source": "warpjobs",
        "source_job_id": "together-ai-staff-software-engineer-645007",
        "sources": ["warpjobs"],
        "first_seen": NOW,
        "last_seen": NOW,
        "active": True,
        "posting_active": True,
        "fingerprint": "fp",
    }
    data.update(overrides)
    return Job(**data)


def test_parse_gh_identifier():
    ref = parse_ats_identifier("gh-togetherai-5214645007")
    assert ref is not None
    assert ref.board == "togetherai"
    assert ref.job_id == "5214645007"


def test_json_ld_resolves_to_greenhouse():
    url = company_apply_url_from_html(_WARPJOBS_HTML)
    assert url == "https://job-boards.greenhouse.io/togetherai/jobs/5214645007"


def test_resolve_rewrites_warpjobs_apply_url():
    job = _job()
    out = resolve_company_apply_urls([job], fetch_text=lambda _url: _WARPJOBS_HTML)
    assert out[0].apply_url == "https://job-boards.greenhouse.io/togetherai/jobs/5214645007"


def test_company_ats_url_is_left_alone():
    job = _job(apply_url="https://job-boards.greenhouse.io/togetherai/jobs/5214645007")
    calls: list[str] = []
    out = resolve_company_apply_urls(
        [job], fetch_text=lambda url: calls.append(url) or ""
    )
    assert calls == []
    assert out[0].apply_url == job.apply_url


def test_warpjobs_is_aggregator():
    assert is_aggregator_apply_url("https://warpjobs.com/jobs/foo/")
    assert is_aggregator_apply_url("https://simplify.jobs/p/abc")
    assert not is_aggregator_apply_url(
        "https://job-boards.greenhouse.io/togetherai/jobs/1"
    )
    assert not is_aggregator_apply_url("https://www.tesla.com/careers/search/job/281271")


def test_prefers_company_career_posting_over_ats_job_board():
    tesla = company_apply_url_from_html(_TESLA_AGGREGATOR_HTML)
    assert tesla == "https://www.tesla.com/careers/search/job/281271"
    stripe = company_apply_url_from_html(_COMPANY_CAREER_HTML)
    assert stripe == "https://stripe.com/jobs/search?gh_jid=7532733"


def test_resolve_rewrites_aggregator_to_tesla_posting_with_slug():
    job = _job(
        company="Tesla",
        title="Software Engineer Intern - Maps",
        apply_url="https://warpjobs.com/jobs/tesla-software-engineer-intern-1/",
    )
    out = resolve_company_apply_urls(
        [job], fetch_text=lambda _url: _TESLA_AGGREGATOR_HTML
    )
    assert out[0].apply_url == (
        "https://www.tesla.com/careers/search/job/software-engineer-intern-maps-281271"
    )


def test_canonicalizes_id_only_tesla_urls_without_fetching():
    job = _job(
        company="Tesla",
        title="Software Engineer Intern - Maps & Navigation Validation",
        apply_url="https://www.tesla.com/careers/search/job/281271",
    )
    calls: list[str] = []
    out = resolve_company_apply_urls(
        [job], fetch_text=lambda url: calls.append(url) or ""
    )
    assert calls == []
    assert out[0].apply_url == (
        "https://www.tesla.com/careers/search/job/"
        "software-engineer-intern-maps-navigation-validation-281271"
    )


def test_tesla_job_id_from_slug_or_numeric_path():
    assert tesla_job_id("https://www.tesla.com/careers/search/job/281271") == "281271"
    assert (
        tesla_job_id(
            "https://www.tesla.com/careers/search/job/internship-software-269198"
        )
        == "269198"
    )
    assert canonical_tesla_apply_url(
        "https://www.tesla.com/careers/search/job/281271",
        "Software Engineer Intern",
    ) == "https://www.tesla.com/careers/search/job/software-engineer-intern-281271"
