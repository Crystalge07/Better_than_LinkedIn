from app.ats.early_career import is_early_career


def test_intern_title_matches():
    assert is_early_career("Software Engineer Intern")
    assert is_early_career("Summer Internship - Finance")
    assert is_early_career("Hardware Co-op")


def test_new_grad_title_matches():
    assert is_early_career("Software Engineer, New Grad")
    assert is_early_career("Early Career Analyst")
    assert is_early_career("University Graduate Program")
    assert is_early_career("Summer Analyst")


def test_rejects_internal_and_recruiters():
    assert not is_early_career("Internal Audit Lead")
    assert not is_early_career("Software Engineer, Internal Tools")
    assert not is_early_career("University Recruiter")
    assert not is_early_career("Senior Software Engineer")
    assert not is_early_career("Internet Network Engineer")
