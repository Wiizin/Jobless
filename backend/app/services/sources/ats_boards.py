"""Public ATS job-board endpoint adapters (Greenhouse, Lever).

These are public, documented, unauthenticated JSON endpoints published by
the ATS vendors themselves for each company's board — not scraping.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.services.cache import build_cache_key, cache_get, cache_set

settings = get_settings()


class ATSBoardError(RuntimeError):
    pass


async def fetch_greenhouse_offers(board_token: str) -> list[dict[str, Any]]:
    """GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

    Board listings change slowly relative to how often the scheduler runs, so
    the raw response is cached briefly (source_cache_ttl_seconds) to avoid
    re-hitting the vendor on every collection pass.
    """
    cache_key = build_cache_key("ats_boards", "greenhouse", board_token)
    cached = await cache_get(cache_key)
    if cached is not None:
        return json.loads(cached)

    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, params={"content": "true"})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ATSBoardError(f"greenhouse fetch failed for {board_token}: {exc}") from exc
    data = resp.json()
    jobs = data.get("jobs", [])
    for job in jobs:
        job["_board_token"] = board_token

    await cache_set(cache_key, json.dumps(jobs), settings.source_cache_ttl_seconds)
    return jobs


async def fetch_lever_offers(company_slug: str) -> list[dict[str, Any]]:
    """GET https://api.lever.co/v0/postings/{slug}?mode=json"""
    cache_key = build_cache_key("ats_boards", "lever", company_slug)
    cached = await cache_get(cache_key)
    if cached is not None:
        return json.loads(cached)

    url = f"https://api.lever.co/v0/postings/{company_slug}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, params={"mode": "json"})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ATSBoardError(f"lever fetch failed for {company_slug}: {exc}") from exc
    data = resp.json()
    for job in data:
        job["_company_slug"] = company_slug

    await cache_set(cache_key, json.dumps(data), settings.source_cache_ttl_seconds)
    return data


async def fetch_all_configured() -> list[dict[str, Any]]:
    """Fetch from every board token/slug configured in settings, concurrently-ish."""
    results: list[dict[str, Any]] = []

    gh_tokens = [t.strip() for t in settings.ats_boards_greenhouse_slugs.split(",") if t.strip()]
    for token in gh_tokens:
        try:
            results.extend(await fetch_greenhouse_offers(token))
        except ATSBoardError:
            continue

    lever_slugs = [s.strip() for s in settings.ats_boards_lever_slugs.split(",") if s.strip()]
    for slug in lever_slugs:
        try:
            results.extend(await fetch_lever_offers(slug))
        except ATSBoardError:
            continue

    return results


def to_common_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Handles both Greenhouse and Lever raw shapes, distinguished by field presence."""
    if "_board_token" in raw:  # Greenhouse
        return {
            "source": "ats_boards",
            "external_id": f"greenhouse:{raw.get('id')}",
            "title": raw.get("title", ""),
            "company": raw["_board_token"],
            "location": (raw.get("location") or {}).get("name", ""),
            "contract_type": "",
            "description": raw.get("content", ""),
            "url": raw.get("absolute_url", ""),
            "posted_date": raw.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        }
    # Lever
    return {
        "source": "ats_boards",
        "external_id": f"lever:{raw.get('id')}",
        "title": raw.get("text", ""),
        "company": raw.get("_company_slug", ""),
        "location": (raw.get("categories") or {}).get("location", ""),
        "contract_type": (raw.get("categories") or {}).get("commitment", ""),
        "description": raw.get("descriptionPlain", raw.get("description", "")),
        "url": raw.get("hostedUrl", ""),
        "posted_date": (
            datetime.fromtimestamp(raw["createdAt"] / 1000, tz=timezone.utc).isoformat()
            if raw.get("createdAt")
            else datetime.now(timezone.utc).isoformat()
        ),
    }
