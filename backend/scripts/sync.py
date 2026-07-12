"""Run the scheduled sync job (one-shot or loop)."""

import argparse
import logging
import sys
import time

from app.store.database import SessionLocal, init_db
from app.sync.runner import run_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _run_once() -> int:
    init_db()
    session = SessionLocal()
    try:
        stats = run_sync(session)
    except Exception:
        logger.exception("Sync run failed")
        return 1
    finally:
        session.close()

    if stats.feeds_ok == 0:
        logger.error("All feeds failed; no changes applied")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync job feeds into Postgres")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously instead of once (for local dev)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between sync runs when --loop is set (default: 3600)",
    )
    args = parser.parse_args()

    if not args.loop:
        return _run_once()

    logger.info("Starting sync loop (interval=%ds)", args.interval)
    while True:
        exit_code = _run_once()
        if exit_code != 0:
            logger.warning("Sync run exited with code %d; continuing loop", exit_code)
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
