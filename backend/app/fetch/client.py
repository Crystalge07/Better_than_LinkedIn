"""HTTP fetching for external feed URLs."""

import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def fetch_json(url: str) -> list | dict:
    """Fetch JSON from a URL. Raises on HTTP or network errors."""
    logger.info("Fetching feed: %s", url)
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
