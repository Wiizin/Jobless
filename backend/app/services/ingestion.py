"""Ties source adapters -> normalizer -> deduplicator -> storage+embedding
-> stage-1/stage-2 matching into the single pipeline the scheduler triggers.

Kept out of scheduler.py so it can be invoked directly (tests, a manual
"collect now" endpoint) without going through APScheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Offer as OfferModel
from app.db.models import OfferStatus, Profile, SearchProfile
from app.db.session import AsyncSessionLocal
from app.schemas.offer import Offer as OfferSchema
from app.services import matching
from app.services.deduplicator import dedupe_batch
from app.services.embeddings import embed_text, offer_embedding_text
from app.services.normalizer import normalize_batch
from app.services.sources import agency_api, aggregator_api, ats_boards

logger = logging.getLogger(__name__)


async def _fetch_all_sources(search_profile: SearchProfile) -> list[OfferSchema]:
    keywords = search_profile.keywords or []
    location = search_profile.locations[0] if search_profile.locations else None

    all_offers: list[OfferSchema] = []

    for source_name, raw_records in [
        ("agency_api", await agency_api.fetch_offers(keywords, location)),
        ("aggregator_api", await aggregator_api.fetch_offers(keywords, location)),
        ("ats_boards", await ats_boards.fetch_all_configured()),
    ]:
        all_offers.extend(normalize_batch(source_name, raw_records))

    return all_offers


async def _existing_offers(db: AsyncSession) -> list[OfferSchema]:
    result = await db.execute(select(OfferModel.source, OfferModel.external_id))
    return [
        OfferSchema(
            source=row.source,
            external_id=row.external_id,
            title="",
            company="",
            location="",
            contract_type="",
            description="",
            url="",
            posted_date=datetime.now(timezone.utc),
        )
        for row in result.all()
    ]


async def collect_for_search_profile(search_profile_id: str) -> int:
    """Run the full ingestion pipeline for one search profile. Returns the
    number of new offers stored."""
    async with AsyncSessionLocal() as db:
        search_profile = await db.get(SearchProfile, search_profile_id)
        if search_profile is None or not search_profile.is_active:
            return 0

        candidates = await _fetch_all_sources(search_profile)
        existing = await _existing_offers(db)
        unique = dedupe_batch(candidates, existing_offers=existing)

        stored = 0
        for offer_schema in unique:
            embedding = embed_text(
                offer_embedding_text(offer_schema.title, offer_schema.company, offer_schema.description)
            )
            offer_row = OfferModel(
                source=offer_schema.source,
                external_id=offer_schema.external_id,
                title=offer_schema.title,
                company=offer_schema.company,
                location=offer_schema.location,
                contract_type=offer_schema.contract_type,
                description=offer_schema.description,
                url=offer_schema.url,
                posted_date=offer_schema.posted_date,
                embedding=embedding,
                status=OfferStatus.new,
            )
            db.add(offer_row)
            stored += 1

        await db.commit()
        logger.info("collect_for_search_profile: stored %d new offers", stored)
        return stored


async def run_matching_for_profile(profile_id: str) -> int:
    """Run stage 1 + stage 2 matching for whatever's new, for one profile.
    Returns the number of offers scored."""
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Profile)
            .where(Profile.id == profile_id)
            .options(
                selectinload(Profile.experiences),
                selectinload(Profile.skills),
                selectinload(Profile.education),
                selectinload(Profile.certifications),
            )
        )
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if profile is None:
            return 0

        candidates = await matching.stage1_filter(db, profile)
        if not candidates:
            return 0
        await matching.score_offers(db, profile, candidates)
        return len(candidates)
