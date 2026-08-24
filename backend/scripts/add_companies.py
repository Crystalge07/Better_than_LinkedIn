"""Verify public career-board JSON APIs and merge rows into companies.json.

Examples:
  PYTHONPATH=. python3 scripts/add_companies.py --url 'https://jobs.lever.co/spotify' --write
  PYTHONPATH=. python3 scripts/add_companies.py --file data/company_url_seeds.json --from-feeds --write
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

from app.ats.career_url import board_identity, parse_career_url
from app.ats.companies_file import (
    company_row,
    load_company_rows,
    merge_company_rows,
    write_companies,
)
from app.ats.discover import (
    DISCOVERY_FEED_URLS,
    BoardCandidate,
    candidates_from_listings,
    candidates_from_seed_file,
)
from app.ats.probe import probe_board
from app.ats.registry import COMPANIES_PATH, CompanyBoard
from app.fetch.client import HttpFetcher, fetch_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("app.fetch.client").setLevel(logging.WARNING)
logger = logging.getLogger("add_companies")

PROBE_TIMEOUT = httpx.Timeout(20.0, connect=8.0)
SEEDS_PATH = Path(__file__).resolve().parents[1] / "data" / "company_url_seeds.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe public ATS JSON APIs and add verified companies"
    )
    parser.add_argument("--url", action="append", default=[], help="Career URL to verify (repeatable)")
    parser.add_argument("--name", help="Company name for --url (single URL only)")
    parser.add_argument("--industry", help="Industry tag for --url or as default for other sources")
    parser.add_argument(
        "--file",
        type=Path,
        help="JSON list of {name, industry, career_url} objects",
    )
    parser.add_argument(
        "--from-feeds",
        action="store_true",
        help="Harvest unique ATS boards from community listings.json feeds",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write verified rows into data/companies.json (otherwise dry-run)",
    )
    parser.add_argument(
        "--reverify",
        action="store_true",
        help="Probe boards that are already in companies.json",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max new boards to probe (0 = no limit)")
    parser.add_argument(
        "--output",
        type=Path,
        default=COMPANIES_PATH,
        help="companies.json path to merge into",
    )
    args = parser.parse_args()

    candidates = _collect_candidates(args)
    if not candidates:
        logger.error("No career URLs to probe. Pass --url, --file, and/or --from-feeds.")
        return 1

    existing_rows = load_company_rows(args.output) if args.output.exists() else []
    existing_ids = _identities_from_rows(existing_rows)
    logger.info("Loaded %d existing companies; %d candidate boards", len(existing_rows), len(candidates))

    new_rows: list[dict] = []
    meta_rows: list[dict] = []
    skipped = 0
    failed = 0
    probed = 0
    with HttpFetcher(timeout=PROBE_TIMEOUT) as http:
        for candidate in candidates:
            identity = board_identity(candidate.parsed)
            if identity in existing_ids and not args.reverify:
                skipped += 1
                if candidate.industry:
                    meta_rows.append(
                        {
                            "name": candidate.name,
                            "ats": candidate.parsed.ats,
                            "career_url": candidate.career_url,
                            "industry": candidate.industry,
                            **(
                                {"board": candidate.parsed.board}
                                if candidate.parsed.ats in {"greenhouse", "lever", "ashby"}
                                else {}
                            ),
                        }
                    )
                logger.debug("Already present: %s", candidate.career_url)
                continue
            if args.limit and probed >= args.limit:
                break
            probed += 1
            if probed % 50 == 0:
                logger.info(
                    "Progress probed=%d added=%d failed=%d remaining~%s",
                    probed,
                    len(new_rows),
                    failed,
                    max(len(candidates) - skipped - probed, 0),
                )
            result = probe_board(
                candidate.parsed,
                fetch_json=http.fetch_json,
                post_json=http.post_json,
                name_hint=candidate.name,
            )
            if not result.ok:
                failed += 1
                logger.info("Skip (%s): %s — %s", result.ats, result.career_url, result.error)
                continue
            board = CompanyBoard(
                name=result.name or candidate.name,
                ats=result.ats,
                industry=candidate.industry or args.industry,
                board=result.board,
                career_url=result.career_url,
                parsed=candidate.parsed,
            )
            new_rows.append(company_row(board))
            existing_ids.add(identity)
            logger.info("OK %s: %s (%s)", board.name, board.career_url, board.ats)

    merged = merge_company_rows(existing_rows, meta_rows + new_rows)
    logger.info(
        "Probe finished: probed=%d added=%d failed=%d already_present=%d total_after_merge=%d",
        probed,
        len(new_rows),
        failed,
        skipped,
        len(merged),
    )

    if args.write:
        write_companies(merged, args.output)
        logger.info("Wrote %d companies to %s", len(merged), args.output)
    else:
        logger.info("Dry-run; pass --write to update %s", args.output)
    return 0


def _collect_candidates(args: argparse.Namespace) -> list[BoardCandidate]:
    candidates: list[BoardCandidate] = []
    for url in args.url:
        parsed = parse_career_url(url)
        candidates.append(
            BoardCandidate(
                name=(args.name or "").strip() or parsed.board or parsed.tenant or url,
                career_url=url,
                industry=args.industry,
                parsed=parsed,
            )
        )
    if args.file:
        file_candidates = candidates_from_seed_file(args.file)
        candidates.extend(file_candidates)
        logger.info("Loaded %d URLs from %s", len(file_candidates), args.file)
    if args.from_feeds and SEEDS_PATH.exists():
        if args.file is None or args.file.resolve() != SEEDS_PATH.resolve():
            seed_candidates = candidates_from_seed_file(SEEDS_PATH)
            candidates.extend(seed_candidates)
            logger.info("Loaded %d seed URLs from %s", len(seed_candidates), SEEDS_PATH)

    if args.from_feeds:
        listings: list[dict] = []
        for feed_url in DISCOVERY_FEED_URLS:
            try:
                payload = fetch_json(feed_url)
            except Exception:
                logger.exception("Discovery feed failed: %s", feed_url)
                continue
            if isinstance(payload, list):
                listings.extend(item for item in payload if isinstance(item, dict))
            logger.info("Fetched %s (%s rows so far)", feed_url, len(listings))
        feed_candidates = candidates_from_listings(listings)
        logger.info("Harvested %d unique ATS boards from feeds", len(feed_candidates))
        candidates.extend(feed_candidates)

    return _dedupe_candidates(candidates)


def _dedupe_candidates(candidates: list[BoardCandidate]) -> list[BoardCandidate]:
    by_id: dict[tuple[str, ...], BoardCandidate] = {}
    for candidate in candidates:
        identity = board_identity(candidate.parsed)
        previous = by_id.get(identity)
        if previous is None:
            by_id[identity] = candidate
            continue
        name = previous.name
        industry = previous.industry or candidate.industry
        if candidate.industry and not previous.industry:
            name = candidate.name or name
        by_id[identity] = BoardCandidate(
            name=name,
            career_url=previous.career_url,
            industry=industry,
            parsed=previous.parsed,
            listing_count=previous.listing_count + candidate.listing_count,
        )
    return list(by_id.values())


def _identities_from_rows(rows: list[dict]) -> set[tuple[str, ...]]:
    from app.ats.registry import _parse_entry

    identities: set[tuple[str, ...]] = set()
    for row in rows:
        try:
            board = _parse_entry(row)
        except Exception:
            continue
        identities.add(board_identity(board.parsed))
    return identities


if __name__ == "__main__":
    sys.exit(main())
