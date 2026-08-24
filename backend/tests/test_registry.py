import json

from app.ats.registry import load_company_boards


def test_load_seed_companies(tmp_path):
    path = tmp_path / "companies.json"
    path.write_text(
        json.dumps(
            {
                "companies": [
                    {"name": "Stripe", "ats": "greenhouse", "board": "stripe"},
                    {
                        "name": "NVIDIA",
                        "ats": "workday",
                        "career_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
                    },
                ]
            }
        )
    )
    boards = load_company_boards(path)
    assert [b.source_tag for b in boards] == [
        "greenhouse:stripe",
        "workday:NVIDIAExternalCareerSite",
    ]


def test_skips_name_only_entry(tmp_path):
    path = tmp_path / "companies.json"
    path.write_text(json.dumps({"companies": [{"name": "Nike"}]}))
    assert load_company_boards(path) == []
