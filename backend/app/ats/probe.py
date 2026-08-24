"""Probe public Greenhouse / Lever / Ashby / Workday JSON APIs."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.ats.ashby import ashby_jobs_url
from app.ats.career_url import ParsedBoard, canonical_career_url
from app.ats.greenhouse import greenhouse_board_url, greenhouse_jobs_url
from app.ats.lever import lever_jobs_url
from app.ats.workday import workday_jobs_url, workday_page_payload, workday_referer_headers


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    ats: str
    career_url: str
    name: str | None
    board: str | None
    error: str | None = None


def probe_board(
    parsed: ParsedBoard,
    *,
    fetch_json,
    post_json,
    name_hint: str | None = None,
) -> ProbeResult:
    career_url = canonical_career_url(parsed)
    name = (name_hint or "").strip() or None
    try:
        if parsed.ats == "greenhouse":
            name = _probe_greenhouse(parsed.board or "", fetch_json, name)
        elif parsed.ats == "lever":
            _probe_lever(parsed.board or "", fetch_json)
        elif parsed.ats == "ashby":
            _probe_ashby(parsed.board or "", fetch_json)
        elif parsed.ats == "workday":
            _probe_workday(parsed, post_json)
        else:
            raise ValueError(f"Unsupported ats {parsed.ats}")
    except Exception as exc:
        return ProbeResult(
            ok=False,
            ats=parsed.ats,
            career_url=career_url,
            name=name,
            board=parsed.board,
            error=str(exc),
        )
    if not name:
        name = _fallback_name(parsed)
    return ProbeResult(
        ok=True,
        ats=parsed.ats,
        career_url=career_url,
        name=name,
        board=parsed.board,
    )


def _probe_greenhouse(board: str, fetch_json, name: str | None) -> str | None:
    payload = fetch_json(greenhouse_jobs_url(board))
    if isinstance(payload, dict):
        if "jobs" not in payload:
            raise ValueError("Greenhouse payload missing jobs list")
    elif not isinstance(payload, list):
        raise ValueError("Greenhouse payload missing jobs list")
    if name:
        return name
    try:
        meta = fetch_json(greenhouse_board_url(board))
    except Exception:
        return name
    if isinstance(meta, dict) and str(meta.get("name") or "").strip():
        return str(meta["name"]).strip()
    return name


def _probe_lever(board: str, fetch_json) -> None:
    payload = fetch_json(lever_jobs_url(board))
    if not isinstance(payload, list):
        if not (isinstance(payload, dict) and isinstance(payload.get("data"), list)):
            raise ValueError("Lever payload missing jobs list")


def _probe_ashby(board: str, fetch_json) -> None:
    payload = fetch_json(ashby_jobs_url(board))
    raw = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ValueError("Ashby payload missing jobs list")


def _probe_workday(parsed: ParsedBoard, post_json) -> None:
    url = workday_jobs_url(parsed)
    headers = workday_referer_headers(parsed)
    last_error: Exception | None = None
    for search_text in ("", "intern"):
        payload = workday_page_payload(offset=0, search_text=search_text)
        try:
            data = post_json(url, payload, extra_headers=headers)
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response is not None and exc.response.status_code == 422:
                continue
            raise
        if isinstance(data, dict) and "jobPostings" in data:
            return
        last_error = ValueError("Workday payload missing jobPostings list")
    if last_error:
        raise last_error
    raise ValueError("Workday payload missing jobPostings list")


def _fallback_name(parsed: ParsedBoard) -> str:
    raw = parsed.board or parsed.tenant or parsed.site or parsed.ats
    cleaned = raw.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in cleaned.split()) or parsed.ats
