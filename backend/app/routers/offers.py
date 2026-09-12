"""Offer listing/detail — the dashboard review surface, plus manual entry.

Nothing here triggers generation or submission. POST /offers/manual is pure
data entry: it stores a hand-pasted posting exactly the way the scheduler
stores an API-sourced one, so it lands at status=new and still has to go
through the same generate -> pending_review -> approve -> download flow.
See routers/documents.py for generation.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_session_token
from app.db.models import Offer, OfferStatus, Profile
from app.db.session import get_db
from app.schemas.offer import ManualOfferIn, OfferDetail, OfferOut
from app.schemas.offer import Offer as OfferSchema
from app.services import matching
from app.services.deduplicator import dedupe_batch
from app.services.embeddings import embed_text, offer_embedding_text

router = APIRouter(prefix="/offers", tags=["offers"], dependencies=[Depends(verify_session_token)])


@router.get("", response_model=list[OfferOut])
async def list_offers(
    min_score: int = Query(default=0, ge=0, le=100),
    status_filter: OfferStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Offer]:
    stmt = select(Offer).where(Offer.match_score.is_not(None), Offer.match_score >= min_score)
    if status_filter is not None:
        stmt = stmt.where(Offer.status == status_filter)
    stmt = stmt.order_by(Offer.match_score.desc(), Offer.posted_date.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _existing_offer_stubs(db: AsyncSession) -> list[OfferSchema]:
    """Minimal OfferSchema stand-ins for everything already stored.

    dedupe_batch only reads source/external_id (exact match) and
    company/title/location (fuzzy), and `_is_duplicate` bails unless the
    companies match exactly — so a blank company never fuzzy-matches a real
    one, and these stubs behave as an exact-(source, external_id) index.
    """
    result = await db.execute(select(Offer.source, Offer.external_id))
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


async def _load_profile_full(db: AsyncSession, profile_id: uuid.UUID) -> Profile | None:
    """Profile with the relationships stage-2 scoring reads, eagerly loaded
    (same pattern as routers/documents.py). Returns None rather than 404 —
    the offer is stored either way; scoring is the optional part."""
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
    return result.scalar_one_or_none()


@router.post("/manual", response_model=OfferDetail, status_code=201)
async def create_manual_offer(
    payload: ManualOfferIn,
    profile_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Offer:
    """Store a hand-pasted posting.

    Data entry only — nothing is submitted anywhere. The stored row is
    indistinguishable from an API-sourced one (status=new), so it goes
    through the same review flow.
    """
    candidate = OfferSchema(
        source="manual",
        # No natural external id for a pasted posting; the URL is the stable
        # dedup key.
        external_id=payload.url,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        contract_type=payload.contract_type,
        description=payload.description,
        url=payload.url,
        posted_date=payload.posted_date or datetime.now(timezone.utc),
    )

    existing = await _existing_offer_stubs(db)
    if not dedupe_batch([candidate], existing_offers=existing):
        raise HTTPException(status_code=409, detail="This looks like a duplicate of an offer already stored")

    embedding = await asyncio.to_thread(
        embed_text,
        offer_embedding_text(candidate.title, candidate.company, candidate.description),
    )

    offer_row = Offer(
        source=candidate.source,
        external_id=candidate.external_id,
        title=candidate.title,
        company=candidate.company,
        location=candidate.location,
        contract_type=candidate.contract_type,
        description=candidate.description,
        url=candidate.url,
        posted_date=candidate.posted_date,
        embedding=embedding,
        status=OfferStatus.new,
    )
    db.add(offer_row)
    await db.commit()
    await db.refresh(offer_row)

    if profile_id is not None:
        profile = await _load_profile_full(db, profile_id)
        if profile is not None:
            await matching.score_offers(db, profile, [offer_row])
            await db.refresh(offer_row)

    return offer_row


@router.get("/{offer_id}", response_model=OfferDetail)
async def get_offer(offer_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Offer:
    offer = await db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


@router.post("/{offer_id}/dismiss", response_model=OfferDetail)
async def dismiss_offer(offer_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Offer:
    offer = await db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.status = OfferStatus.dismissed
    await db.commit()
    await db.refresh(offer)
    return offer
