"""Scheduled sync: fetch feeds, normalize, diff/upsert into Postgres."""

from app.sync.runner import run_sync

__all__ = ["run_sync"]
