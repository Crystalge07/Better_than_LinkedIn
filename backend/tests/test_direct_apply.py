from datetime import datetime, timezone

from app.ats.direct_apply import (
    company_apply_url_from_html,
    is_aggregator_apply_url,
    resolve_company_apply_urls,
)
from app.ats.job_url import parse_ats_identifier
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
    assert not is_aggregator_apply_url(
        "https://job-boards.greenhouse.io/togetherai/jobs/1"
    )
