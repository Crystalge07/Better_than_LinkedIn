from app.normalize.apply_url import urls_conflict
from app.normalize.dedupe import merge_jobs
from tests.conftest import expected_merged_count, jobs_from_fixture_group


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
    assert urls_conflict(left, right)


def test_urls_conflict_different_netloc_always():
    left = "https://apply.careers.microsoft.com/careers/job/1970393556744805"
    right = "https://jobs.careers.microsoft.com/global/en/job/1847616/Firmware-Engineer"
    assert urls_conflict(left, right)


def test_urls_compatible_identical():
    url = "https://jobs.ashbyhq.com/ellipsislabs/02136b22-35b1-4b3d-8bef-567c3380a849/"
    assert not urls_conflict(url, url)
