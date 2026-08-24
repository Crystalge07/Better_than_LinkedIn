"""Adapter for SimplifyJobs internship listings.json feeds."""

from app.normalize.adapters.listings_json import ListingsJsonAdapter

FEED_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/"
    ".github/scripts/listings.json"
)
FEED_URL_2027 = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/"
    ".github/scripts/listings.json"
)
FEED_TAG = "simplify_internships"
FEED_TAG_2027 = "simplify_internships_2027"


class SimplifyInternshipsAdapter(ListingsJsonAdapter):
    def __init__(self, source_name: str = FEED_TAG, feed_url: str = FEED_URL) -> None:
        super().__init__(source_name, feed_url)
