from app.ats.career_url import parse_career_url


def test_parse_greenhouse_job_board():
    parsed = parse_career_url("https://job-boards.greenhouse.io/stripe")
    assert parsed.ats == "greenhouse"
    assert parsed.board == "stripe"


def test_parse_lever():
    parsed = parse_career_url("https://jobs.lever.co/spotify")
    assert parsed.ats == "lever"
    assert parsed.board == "spotify"


def test_parse_ashby():
    parsed = parse_career_url("https://jobs.ashbyhq.com/openai")
    assert parsed.ats == "ashby"
    assert parsed.board == "openai"


def test_parse_workday_with_language():
    parsed = parse_career_url(
        "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
    )
    assert parsed.ats == "workday"
    assert parsed.host == "nvidia.wd5.myworkdayjobs.com"
    assert parsed.tenant == "nvidia"
    assert parsed.site == "NVIDIAExternalCareerSite"


def test_parse_greenhouse_embed_for_param():
    parsed = parse_career_url("https://boards.greenhouse.io/embed/job_app?for=stripe")
    assert parsed.ats == "greenhouse"
    assert parsed.board == "stripe"


def test_parse_greenhouse_job_posting_path():
    parsed = parse_career_url("https://job-boards.greenhouse.io/stripe/jobs/12345")
    assert parsed.board == "stripe"


def test_parse_workday_job_posting_uses_site_not_location():
    parsed = parse_career_url(
        "https://pg.wd5.myworkdayjobs.com/1000/job/CINCINNATI-GENERAL-OFFICES/Data-Engineer_R1"
    )
    assert parsed.tenant == "pg"
    assert parsed.site == "1000"


def test_parse_myworkdaysite():
    parsed = parse_career_url(
        "https://wd1.myworkdaysite.com/recruiting/mdlz/External/job/Chicago/Intern_R1"
    )
    assert parsed.ats == "workday"
    assert parsed.host == "wd1.myworkdaysite.com"
    assert parsed.tenant == "mdlz"
    assert parsed.site == "External"
