"""Deprecated wrapper — use scripts/sync.py instead."""

import logging
import sys

from app.store.database import SessionLocal, init_db
from app.sync.runner import run_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    logger.warning("ingest.py is deprecated; use scripts/sync.py")
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
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
