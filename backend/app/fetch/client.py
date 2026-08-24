"""HTTP fetching for external feed and ATS URLs."""

import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BetterThanLinkedIn/0.1; "
        "+https://github.com/crystalge/Better_than_LinkedIn)"
    ),
    "Accept": "application/json",
}


def _client(headers: dict | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers=headers or DEFAULT_HEADERS,
    )


def fetch_json(url: str) -> list | dict:
    """GET JSON from a URL. Raises on HTTP or network errors."""
    logger.info("Fetching: %s", url)
    with _client() as http:
        response = http.get(url)
        response.raise_for_status()
        return response.json()


def fetch_text(url: str) -> str:
    """GET a text/markdown feed. Raises on HTTP or network errors."""
    logger.info("Fetching text: %s", url)
    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = "text/plain, text/markdown, text/html;q=0.9, */*;q=0.8"
    with _client(headers) as http:
        response = http.get(url)
        response.raise_for_status()
        return response.text


def post_json(
    url: str,
    payload: dict,
    extra_headers: dict | None = None,
) -> list | dict:
    """POST JSON and return the parsed body. Raises on HTTP or network errors."""
    logger.info("Posting: %s", url)
    headers = dict(DEFAULT_HEADERS)
    headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    with _client(headers) as http:
        response = http.post(url, json=payload)
        response.raise_for_status()
        return response.json()
