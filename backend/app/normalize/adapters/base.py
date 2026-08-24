"""Feed adapters map raw JSON into the internal Job schema."""

from abc import ABC, abstractmethod

from app.schemas.job import Job


class FeedAdapter(ABC):
    source_name: str
    feed_url: str

    @abstractmethod
    def normalize(self, raw: list | dict) -> list[Job]:
        """Map raw feed JSON to normalized Job objects."""

    def fetch_and_normalize(self, fetch_json, fetch_text=None) -> list[Job]:
        raw = fetch_json(self.feed_url)
        return self.normalize(raw)
