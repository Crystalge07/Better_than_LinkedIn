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
