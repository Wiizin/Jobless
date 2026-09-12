"""Normalized Offer schema — shared shape all source adapters map into."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Offer(BaseModel):
    """Common schema every source adapter normalizes into (normalizer.py)."""

    source: str
    external_id: str
    title: str
    company: str
    location: str
    contract_type: str
    description: str
    url: str
    posted_date: datetime


class ManualOfferIn(BaseModel):
    """A posting pasted in by hand — the only path for sources with no
    official API (e.g. a company career page, or a platform whose terms
    prohibit automated access). Whoever is pasting this — the user, or
    Claude relaying something found via web search — is vouching that the
    text below is copied from a real, currently-live posting."""

    title: str
    company: str
    location: str
    contract_type: str
    description: str
    url: str
    posted_date: datetime | None = None


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    company: str
    location: str | None
    contract_type: str | None
    description: str
    url: str
    posted_date: datetime | None
    match_score: int | None
    match_reasoning: str | None
    missing_skills: list[str]
    dealbreakers: list[str]
    status: str
    created_at: datetime


class OfferDetail(OfferOut):
    pass
