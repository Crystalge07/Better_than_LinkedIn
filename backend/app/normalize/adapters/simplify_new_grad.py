"""Adapter for SimplifyJobs New-Grad-Positions listings.json feed."""

from app.normalize.adapters.listings_json import ListingsJsonAdapter

FEED_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/"
    ".github/scripts/listings.json"
)
FEED_TAG = "simplify_new_grad"


class SimplifyNewGradAdapter(ListingsJsonAdapter):
    def __init__(self) -> None:
        super().__init__(FEED_TAG, FEED_URL)
