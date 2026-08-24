from datetime import datetime, timedelta, timezone

from app.normalize.adapters.speedyapply import parse_speedyapply_markdown

SAMPLE = """
## FAANG+

| Company | Position | Location | Salary | Posting | Age |
|---|---|---|---|---|---|
| <a href="https://www.microsoft.com"><strong>Microsoft</strong></a> | AI Software Engineering Intern - Edge | Washington, DC +1 | $52/hr | <a href="https://apply.careers.microsoft.com/careers/job/1970393556979054"><img src="https://i.imgur.com/JpkfjIq.png" alt="Apply" width="70"/></a> | 2d |
| ClosedCorp | Intern | Remote | $20/hr | | 1d |

### Other

| Company | Position | Location | Posting | Age |
|---|---|---|---|---|
| <a href="https://www.nvidia.com"><strong>NVIDIA</strong></a> | Software Engineering Intern | Santa Clara, CA | <a href="https://nvidia.wd5.myworkdayjobs.com/job/JR2023492"><img src="https://i.imgur.com/JpkfjIq.png" alt="Apply"/></a> | 4d |
"""


def test_parse_speedyapply_extracts_apply_href_not_company_site():
    now = datetime(2026, 8, 23, tzinfo=timezone.utc)
    jobs = parse_speedyapply_markdown(SAMPLE, feed_tag="speedyapply_swe_2027", seen_at=now)
    assert len(jobs) == 2
    microsoft = next(job for job in jobs if job.company == "Microsoft")
    assert microsoft.title == "AI Software Engineering Intern - Edge"
    assert microsoft.apply_url.startswith("https://apply.careers.microsoft.com/")
    assert microsoft.date_posted == now - timedelta(days=2)
    assert microsoft.source == "speedyapply_swe_2027"


def test_parse_speedyapply_skips_rows_without_apply_link():
    now = datetime(2026, 8, 23, tzinfo=timezone.utc)
    jobs = parse_speedyapply_markdown(SAMPLE, feed_tag="speedyapply_swe_2027", seen_at=now)
    assert all(job.company != "ClosedCorp" for job in jobs)


def test_parse_speedyapply_handles_tables_without_salary_column():
    now = datetime(2026, 8, 23, tzinfo=timezone.utc)
    jobs = parse_speedyapply_markdown(SAMPLE, feed_tag="speedyapply_swe_2027", seen_at=now)
    nvidia = next(job for job in jobs if job.company == "NVIDIA")
    assert "myworkdayjobs.com" in nvidia.apply_url
    assert nvidia.locations == ["Santa Clara, CA"]
