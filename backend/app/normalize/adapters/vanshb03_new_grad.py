"""Adapter for vanshb03 new-grad listings.json feeds."""

from app.normalize.adapters.listings_json import ListingsJsonAdapter

FEED_URL = (
    "https://raw.githubusercontent.com/vanshb03/New-Grad-2026/dev/"
    ".github/scripts/listings.json"
)
FEED_URL_2027 = (
    "https://raw.githubusercontent.com/vanshb03/New-Grad-2027/dev/"
    ".github/scripts/listings.json"
)
FEED_TAG = "vanshb03_new_grad"
FEED_TAG_2027 = "vanshb03_new_grad_2027"


class Vanshb03NewGradAdapter(ListingsJsonAdapter):
    def __init__(self, source_name: str = FEED_TAG, feed_url: str = FEED_URL) -> None:
        super().__init__(source_name, feed_url)
