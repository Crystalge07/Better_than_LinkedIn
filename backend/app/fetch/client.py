"""HTTP fetching for external feed and ATS URLs."""

from __future__ import annotations

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
TESLA_JSON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tesla.com/careers/search/",
    "Origin": "https://www.tesla.com",
}


def _client(headers: dict | None = None, timeout: httpx.Timeout | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=timeout or DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers=headers or DEFAULT_HEADERS,
    )


class HttpFetcher:
    """Reusable HTTP client for many ATS requests in one sync or probe run."""

    def __init__(self, timeout: httpx.Timeout | None = None) -> None:
        self._http = _client(timeout=timeout)

    def fetch_json(self, url: str) -> list | dict:
        logger.info("Fetching: %s", url)
        headers = TESLA_JSON_HEADERS if "tesla.com/cua-api" in url else None
        response = self._http.get(url, headers=headers) if headers else self._http.get(url)
        response.raise_for_status()
        return response.json()

    def fetch_text(self, url: str) -> str:
        logger.info("Fetching text: %s", url)
        headers = dict(DEFAULT_HEADERS)
        headers["Accept"] = "text/plain, text/markdown, text/html;q=0.9, */*;q=0.8"
        response = self._http.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def post_json(
        self,
        url: str,
        payload: dict,
        extra_headers: dict | None = None,
    ) -> list | dict:
        logger.info("Posting: %s", url)
        headers = dict(DEFAULT_HEADERS)
        headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        response = self._http.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> HttpFetcher:
        return self

    def __exit__(self, *args) -> None:
        self.close()


def fetch_json(url: str) -> list | dict:
    """GET JSON from a URL. Raises on HTTP or network errors."""
    with HttpFetcher() as http:
        return http.fetch_json(url)


def fetch_text(url: str) -> str:
    """GET a text/markdown feed. Raises on HTTP or network errors."""
    with HttpFetcher() as http:
        return http.fetch_text(url)


def post_json(
    url: str,
    payload: dict,
    extra_headers: dict | None = None,
) -> list | dict:
    """POST JSON and return the parsed body. Raises on HTTP or network errors."""
    with HttpFetcher() as http:
        return http.post_json(url, payload, extra_headers=extra_headers)
