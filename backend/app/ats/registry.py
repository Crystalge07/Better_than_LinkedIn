"""Load company career boards from backend/data/companies.json."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.ats.career_url import ParsedBoard, parse_career_url

logger = logging.getLogger(__name__)

COMPANIES_PATH = Path(__file__).resolve().parents[2] / "data" / "companies.json"
SUPPORTED_ATS = {"greenhouse", "lever", "ashby", "workday"}


@dataclass(frozen=True)
class CompanyBoard:
    name: str
    ats: str
    industry: str | None
    board: str | None
    career_url: str | None
    parsed: ParsedBoard

    @property
    def source_tag(self) -> str:
        ident = self.parsed.board or self.parsed.site or self.name.lower().replace(" ", "")
        return f"{self.ats}:{ident}"[:128]


def load_company_boards(path: Path | None = None) -> list[CompanyBoard]:
    data_path = path or COMPANIES_PATH
    raw = json.loads(data_path.read_text())
    entries = raw.get("companies", raw if isinstance(raw, list) else [])
    boards: list[CompanyBoard] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            boards.append(_parse_entry(entry))
        except Exception:
            logger.exception("Skipping invalid company entry: %s", entry.get("name", entry))
    logger.info("Loaded %d company boards from %s", len(boards), data_path)
    return boards


def _parse_entry(entry: dict) -> CompanyBoard:
    name = str(entry.get("name") or "").strip()
    if not name:
        raise ValueError("company entry missing name")
    ats = str(entry.get("ats") or "").strip().lower()
    board = str(entry.get("board") or "").strip() or None
    career_url = str(entry.get("career_url") or "").strip() or None
    industry = str(entry.get("industry") or "").strip() or None

    if career_url:
        parsed = parse_career_url(career_url)
        if ats and ats != parsed.ats:
            raise ValueError(f"{name}: ats={ats} does not match URL ats={parsed.ats}")
        ats = parsed.ats
        board = board or parsed.board
    else:
        if ats not in SUPPORTED_ATS:
            raise ValueError(f"{name}: unsupported ats {ats!r}")
        if ats == "workday":
            raise ValueError(f"{name}: Workday requires career_url")
        if not board:
            raise ValueError(f"{name}: greenhouse/lever/ashby require board or career_url")
        parsed = ParsedBoard(ats=ats, board=board)

    return CompanyBoard(
        name=name,
        ats=ats,
        industry=industry,
        board=board,
        career_url=career_url,
        parsed=parsed,
    )
