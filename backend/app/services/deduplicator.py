"""Cross-source dedup using rapidfuzz on (company, title, location).

Runs before storage: candidates are checked against offers already in the
DB (passed in) and against each other within the same ingestion batch.
"""
from __future__ import annotations

from rapidfuzz import fuzz

from app.config import get_settings
from app.schemas.offer import Offer

settings = get_settings()


def _key(offer: Offer) -> str:
    return f"{offer.company.strip().lower()}|{offer.title.strip().lower()}|{offer.location.strip().lower()}"


def _is_duplicate(candidate: Offer, existing: Offer, threshold: int) -> bool:
    if candidate.company.strip().lower() != existing.company.strip().lower():
        return False
    score = fuzz.token_sort_ratio(_key(candidate), _key(existing))
    return score >= threshold


def dedupe_batch(
    candidates: list[Offer],
    existing_offers: list[Offer] | None = None,
    threshold: int | None = None,
) -> list[Offer]:
    """Return candidates with duplicates removed.

    - Exact (source, external_id) matches against `existing_offers` are
      dropped outright (already stored).
    - Fuzzy (company, title, location) matches above `threshold` — whether
      against `existing_offers` or an earlier item in this same batch — are
      also dropped, keeping the first occurrence.
    """
    threshold = threshold or settings.dedup_fuzzy_threshold
    existing_offers = existing_offers or []

    existing_ids = {(o.source, o.external_id) for o in existing_offers}
    seen: list[Offer] = list(existing_offers)

    unique: list[Offer] = []
    for candidate in candidates:
        if (candidate.source, candidate.external_id) in existing_ids:
            continue

        if any(_is_duplicate(candidate, other, threshold) for other in seen):
            continue

        unique.append(candidate)
        seen.append(candidate)

    return unique
