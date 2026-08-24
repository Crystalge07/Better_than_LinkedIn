"""Title filter for intern / new-grad / early-career postings."""

import re

_EXCLUDE = re.compile(
    r"\b(recruiter|recruiting|recruitment|sourcer|talent acquisition)\b",
    re.IGNORECASE,
)

_INCLUDE = re.compile(
    r"""
    \binternships?\b
    | \binterns?\b
    | \bco[\s-]?ops?\b
    | new[\s-]?grads?
    | recent[\s-]?grads?
    | early[\s-]?career
    | (?:graduate|grad)[\s-]+(?:program|programme|scheme)
    | rotational[\s-]+(?:program|programme)
    | summer[\s-]+analyst
    | winter[\s-]+analyst
    | off[\s-]?cycle
    | university[\s-]+(?:grad|graduate|hire)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_early_career(title: str) -> bool:
    """True for intern / new-grad / early-career titles, not recruiters or 'internal' roles."""
    if not title or _EXCLUDE.search(title):
        return False
    return bool(_INCLUDE.search(title))
