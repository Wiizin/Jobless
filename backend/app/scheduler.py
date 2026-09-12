"""APScheduler setup — in-process, interval-based. No Redis/worker queue.

Triggers offer collection (and matching) on an interval for every active
SearchProfile. Started/stopped from main.py's lifespan handler.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db.models import SearchProfile
from app.db.session import AsyncSessionLocal
from app.services.ingestion import collect_for_search_profile, run_matching_for_profile

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def run_collection_cycle() -> None:
    """One full cycle: collect new offers for every active search profile,
    then run matching for the owning profile."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SearchProfile).where(SearchProfile.is_active.is_(True)))
        search_profiles = list(result.scalars().all())

    for sp in search_profiles:
        try:
            stored = await collect_for_search_profile(str(sp.id))
            logger.info("search_profile=%s stored=%d", sp.id, stored)
        except Exception:
            logger.exception("collection failed for search_profile=%s", sp.id)
            continue

        try:
            scored = await run_matching_for_profile(str(sp.profile_id))
            logger.info("search_profile=%s scored=%d", sp.id, scored)
        except Exception:
            logger.exception("matching failed for profile=%s", sp.profile_id)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        run_collection_cycle,
        trigger="interval",
        minutes=settings.collection_interval_minutes,
        id="collection_cycle",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("scheduler started, interval=%d minutes", settings.collection_interval_minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler stopped")
