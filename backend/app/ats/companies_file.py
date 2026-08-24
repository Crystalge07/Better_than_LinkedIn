"""Read/write backend/data/companies.json."""

from __future__ import annotations

import json
from pathlib import Path

from app.ats.career_url import board_identity, canonical_career_url
from app.ats.registry import COMPANIES_PATH, CompanyBoard, load_company_boards

HOW_TO_ADD = (
    "A company NAME is not enough. Add the public career-board identifier: "
    "Greenhouse/Lever/Ashby `board` slug, or a Workday `career_url` like "
    "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite. Paste a "
    "jobs.lever.co / job-boards.greenhouse.io / jobs.ashbyhq.com / "
    "myworkdayjobs.com / myworkdaysite.com URL in career_url and ats+board "
    "will be inferred. Or run: PYTHONPATH=. python3 scripts/add_companies.py "
    "--url 'https://jobs.lever.co/spotify' --write. We only pull intern / "
    "new-grad / early-career titles from company boards. Do not invent slugs; "
    "the helper probes the public JSON API first."
)


def company_row(board: CompanyBoard) -> dict:
    row: dict = {
        "name": board.name,
        "ats": board.ats,
        "career_url": canonical_career_url(board.parsed),
    }
    if board.industry:
        row["industry"] = board.industry
    if board.ats in {"greenhouse", "lever", "ashby"} and board.board:
        row["board"] = board.board
    return row


def merge_company_rows(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Keep first identity; fill missing industry/career_url/board from later rows."""
    by_id: dict[tuple[str, ...], dict] = {}
    for row in existing + incoming:
        board = _row_to_board(row)
        if board is None:
            continue
        identity = board_identity(board.parsed)
        current = company_row(board)
        previous = by_id.get(identity)
        if previous is None:
            by_id[identity] = current
            continue
        if not previous.get("industry") and current.get("industry"):
            previous["industry"] = current["industry"]
        if not previous.get("career_url") and current.get("career_url"):
            previous["career_url"] = current["career_url"]
        if not previous.get("board") and current.get("board"):
            previous["board"] = current["board"]
    return sorted(by_id.values(), key=lambda row: (row["name"].lower(), row["career_url"]))


def write_companies(rows: list[dict], path: Path | None = None) -> None:
    dest = path or COMPANIES_PATH
    payload = {"how_to_add": HOW_TO_ADD, "companies": rows}
    dest.write_text(json.dumps(payload, indent=2) + "\n")


def load_company_rows(path: Path | None = None) -> list[dict]:
    boards = load_company_boards(path)
    return [company_row(board) for board in boards]


def _row_to_board(row: dict) -> CompanyBoard | None:
    from app.ats.registry import _parse_entry

    try:
        return _parse_entry(row)
    except Exception:
        return None
