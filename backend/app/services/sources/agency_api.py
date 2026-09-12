"""National employment agency API adapter.

Placeholder client — wire up the specific agency's official free API here
(e.g. France Travail / Pole Emploi API, or the equivalent for your country).
No scraping: this must only call documented, authorized endpoints.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.services.cache import build_cache_key, cache_get, cache_set

settings = get_settings()


class AgencyAPIError(RuntimeError):
    pass


async def fetch_offers(keywords: list[str], location: str | None = None) -> list[dict[str, Any]]:
    """Fetch raw offers from the national employment agency API.

    Returns raw dicts in the source's native shape — normalizer.py maps them
    into the common Offer schema. Returns [] rather than raising when the
    adapter isn't configured yet, so the scheduler can run before all
    sources are wired up.
    """
    if not settings.agency_api_base_url or not settings.agency_api_key:
        return []

    cache_key = build_cache_key("agency_api", ",".join(keywords), location or "")
    cached = await cache_get(cache_key)
    if cached is not None:
        return json.loads(cached)

    params = {"q": " ".join(keywords)}
    if location:
        params["location"] = location

    headers = {"Authorization": f"Bearer {settings.agency_api_key}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                f"{settings.agency_api_base_url}/offers/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgencyAPIError(f"agency_api request failed: {exc}") from exc

    data = resp.json()
    results = data.get("results", [])

    await cache_set(cache_key, json.dumps(results), settings.source_cache_ttl_seconds)
    return results


def to_common_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Map one raw agency-API record into the fields normalizer.py expects.

    Field names below are placeholders — adjust to the real agency schema
    once an API key is available.
    """
    return {
        "source": "agency_api",
        "external_id": str(raw.get("id")),
        "title": raw.get("title", ""),
        "company": raw.get("company", {}).get("name", "") if isinstance(raw.get("company"), dict) else raw.get("company", ""),
        "location": raw.get("location", ""),
        "contract_type": raw.get("contract_type", ""),
        "description": raw.get("description", ""),
        "url": raw.get("url", ""),
        "posted_date": raw.get("posted_date") or datetime.now(timezone.utc).isoformat(),
    }
