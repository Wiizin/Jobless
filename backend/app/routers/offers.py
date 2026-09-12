"""Offer listing/detail — the dashboard review surface.

Nothing here triggers generation or submission; this is read-only plus a
dismiss action. See routers/documents.py for generation.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_session_token
from app.db.models import Offer, OfferStatus
from app.db.session import get_db
from app.schemas.offer import OfferDetail, OfferOut

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
