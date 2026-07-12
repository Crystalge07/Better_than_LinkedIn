from app.normalize.fingerprint import compute_fingerprint, normalize_company, normalize_title
from tests.conftest import jobs_from_fixture_group


def test_normalize_title_strips_new_grad_prefix():
    assert normalize_title("New Grad 2026: Software Engineer") == "software engineer"


def test_normalize_company_strips_suffix():
    assert "inc" not in normalize_company("Great American Insurance Company, Inc.")


def test_visa_pair_shares_fingerprint_across_feeds():
    jobs = jobs_from_fixture_group("merge_false_visa_highlands_ranch")
    assert jobs[0].fingerprint == jobs[1].fingerprint


def test_microsoft_swe_pair_shares_fingerprint():
    jobs = jobs_from_fixture_group("merge_false_microsoft_swe_redmond")
    assert len({job.fingerprint for job in jobs}) == 1


def test_distinct_jobs_have_distinct_fingerprints():
    left = compute_fingerprint("Apple", "Software Engineer", ["Cupertino, CA"])
    right = compute_fingerprint("Apple", "Hardware Engineer", ["Cupertino, CA"])
    assert left != right
