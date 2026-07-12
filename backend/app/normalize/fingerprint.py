"""Fingerprint helpers — basic normalization for step 1; expanded in step 3."""

import hashlib
import re


_COMPANY_SUFFIXES = re.compile(
    r"\b(inc\.?|llc\.?|l\.?l\.?c\.?|corp\.?|corporation|technologies|technology|co\.?)\b",
    re.IGNORECASE,
)


def normalize_company(name: str) -> str:
    cleaned = name.strip().lower()
    cleaned = _COMPANY_SUFFIXES.sub("", cleaned)
    return re.sub(r"[^\w\s]", "", cleaned).strip()


def normalize_title(title: str) -> str:
    cleaned = title.strip().lower()
    cleaned = re.sub(r"^(new grad \d{4}:?\s*|intern(?:ship)?\s*[-–]?\s*)", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_location(location: str) -> str:
    """Best-effort canonical form; full US state mapping in step 3."""
    return re.sub(r"\s+", " ", location.strip())


def compute_fingerprint(company: str, title: str, locations: list[str]) -> str:
    """Hash of normalized company + title + primary location."""
    primary_location = normalize_location(locations[0]) if locations else ""
    key = "|".join(
        [
            normalize_company(company),
            normalize_title(title),
            primary_location.lower(),
        ]
    )
    return hashlib.sha256(key.encode()).hexdigest()
