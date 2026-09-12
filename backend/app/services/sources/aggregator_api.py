"""Adzuna-style job-aggregator API adapter (official, key-based, no scraping)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


class AggregatorAPIError(RuntimeError):
    pass


async def fetch_offers(
    keywords: list[str], location: str | None = None, country: str = "us", page: int = 1
) -> list[dict[str, Any]]:
    """Fetch raw offers from the aggregator API (e.g. Adzuna /search/{page})."""
    if not settings.aggregator_app_id or not settings.aggregator_app_key:
        return []

    params = {
        "app_id": settings.aggregator_app_id,
        "app_key": settings.aggregator_app_key,
        "what": " ".join(keywords),
        "results_per_page": 50,
    }
    if location:
        params["where"] = location

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                f"{settings.aggregator_api_base_url}/jobs/{country}/search/{page}",
                params=params,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AggregatorAPIError(f"aggregator_api request failed: {exc}") from exc

    data = resp.json()
    return data.get("results", [])


def to_common_dict(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "aggregator_api",
        "external_id": str(raw.get("id")),
        "title": raw.get("title", ""),
        "company": (raw.get("company") or {}).get("display_name", ""),
        "location": (raw.get("location") or {}).get("display_name", ""),
        "contract_type": raw.get("contract_time") or raw.get("contract_type") or "",
        "description": raw.get("description", ""),
        "url": raw.get("redirect_url", ""),
        "posted_date": raw.get("created") or datetime.now(timezone.utc).isoformat(),
    }
