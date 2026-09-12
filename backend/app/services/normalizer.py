"""Maps raw per-source dicts into the common Offer schema (schemas/offer.py)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil import parser as date_parser  # lightweight, tolerant date parsing

from app.schemas.offer import Offer
from app.services.sources import agency_api, aggregator_api, ats_boards

_TO_COMMON = {
    "agency_api": agency_api.to_common_dict,
    "aggregator_api": aggregator_api.to_common_dict,
    "ats_boards": ats_boards.to_common_dict,
}


def _parse_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return date_parser.parse(str(value))
    except (ValueError, TypeError):
        return datetime.utcnow()


def normalize(source: str, raw: dict[str, Any]) -> Offer:
    """Normalize a single raw record from `source` into an Offer."""
    to_common = _TO_COMMON.get(source)
    if to_common is None:
        raise ValueError(f"unknown source: {source}")

    common = to_common(raw)
    common["posted_date"] = _parse_date(common.get("posted_date"))

    # Guard against missing/blank required text fields rather than letting
    # Pydantic raise deep in a batch job.
    common["location"] = common.get("location") or "Unspecified"
    common["contract_type"] = common.get("contract_type") or "Unspecified"
    common["description"] = common.get("description") or ""

    return Offer(**common)


def normalize_batch(source: str, raw_records: list[dict[str, Any]]) -> list[Offer]:
    normalized: list[Offer] = []
    for raw in raw_records:
        try:
            normalized.append(normalize(source, raw))
        except Exception:
            # One bad record shouldn't drop the whole batch; the ingestion
            # layer logs skips via its own logger.
            continue
    return normalized
