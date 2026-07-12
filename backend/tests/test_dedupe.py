from app.normalize.apply_url import pick_preferred_apply_url, urls_conflict
from app.normalize.dedupe import merge_job_group, merge_jobs
from tests.conftest import expected_merged_count, jobs_from_fixture_group


def test_merge_true_microsoft_firmware():
    jobs = jobs_from_fixture_group("merge_true_microsoft_firmware")
    merged = merge_jobs(jobs)
    assert len(merged) == expected_merged_count("merge_true_microsoft_firmware")
    assert set(merged[0].sources) == {"simplify_internships", "vanshb03_new_grad"}


def test_merge_false_microsoft_swe_redmond():
    jobs = jobs_from_fixture_group("merge_false_microsoft_swe_redmond")
    merged = merge_jobs(jobs)
    assert len(merged) == len(jobs) == expected_merged_count("merge_false_microsoft_swe_redmond")


def test_merge_false_visa_highlands_ranch():
    jobs = jobs_from_fixture_group("merge_false_visa_highlands_ranch")
    merged = merge_jobs(jobs)
    assert len(merged) == len(jobs)


def test_merge_false_ellipsis_labs_ashby():
    jobs = jobs_from_fixture_group("merge_false_ellipsis_labs_ashby")
    merged = merge_jobs(jobs)
    assert len(merged) == len(jobs)


def test_merge_false_amat_data_scientist():
    jobs = jobs_from_fixture_group("merge_false_amat_data_scientist")
    merged = merge_jobs(jobs)
    assert len(merged) == len(jobs)


def test_merge_job_group_prefers_earlier_date_posted():
    jobs = jobs_from_fixture_group("merge_true_microsoft_firmware")
    merged = merge_job_group(jobs)
    assert merged.date_posted == min(job.date_posted for job in jobs)


def test_merge_job_group_prefers_direct_apply_url():
    jobs = jobs_from_fixture_group("merge_true_microsoft_firmware")
    merged = merge_job_group(jobs)
    preferred = pick_preferred_apply_url([job.apply_url for job in jobs])
    assert merged.apply_url == preferred


def test_merge_jobs_is_idempotent():
    jobs = jobs_from_fixture_group("merge_false_microsoft_swe_redmond")
    once = merge_jobs(jobs)
    twice = merge_jobs(once)
    assert len(twice) == len(once)
    assert {(job.fingerprint, job.apply_url, tuple(job.sources)) for job in once} == {
        (job.fingerprint, job.apply_url, tuple(job.sources)) for job in twice
    }


def test_urls_conflict_same_host_different_paths():
    left = "https://jobs.careers.microsoft.com/global/en/job/1826495/Software-Engineer"
    right = "https://jobs.careers.microsoft.com/global/en/job/1857028/Software-Engineer"
    counts = {"jobs.careers.microsoft.com": 2}
    assert urls_conflict(left, right, netloc_counts=counts)


def test_urls_allow_syndication_when_each_host_is_unique():
    left = "https://apply.careers.microsoft.com/careers/job/1970393556744805"
    right = "https://jobs.careers.microsoft.com/global/en/job/1847616/Firmware-Engineer"
    counts = {
        "apply.careers.microsoft.com": 1,
        "jobs.careers.microsoft.com": 1,
    }
    assert not urls_conflict(left, right, netloc_counts=counts)
