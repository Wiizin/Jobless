"""Two-stage offer matching.

Stage 1: cheap cosine-similarity filter via pgvector — drops offers whose
embedding is far from the profile's embedding before any LLM call happens.

Stage 2: the LLM (via OpenRouter) scores only what survives stage 1 and
returns a structured MatchResult (schemas/match.py) — never free text.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Offer, OfferStatus, Profile
from app.schemas.match import MatchResult
from app.services.cache import build_cache_key, cache_get, cache_set
from app.services.embeddings import embed_text, offer_embedding_text, profile_embedding_text
from app.services.llm_client import call_structured

settings = get_settings()

_SYSTEM_PROMPT = """You score how well a job/internship offer matches a candidate's profile.
Respond ONLY by calling the `submit_match_result` tool with a score (0-100), a short
grounded reasoning, a list of missing_skills the offer requires that the profile lacks,
and a list of dealbreakers (hard mismatches like required work authorization, seniority
mismatch, or incompatible location/contract type). Base every claim strictly on the
profile and offer text provided — never assume unstated candidate qualifications."""


async def stage1_filter(
    db: AsyncSession, profile: Profile, limit: int = 200
) -> list[Offer]:
    """Cosine-similarity filter (pgvector `<=>` = cosine distance) against
    offers that haven't been scored yet."""
    skills = [s.name for s in profile.skills]
    titles = [e.title for e in profile.experiences]
    profile_text = profile_embedding_text(profile.summary or "", skills, titles)
    profile_vector = await asyncio.to_thread(embed_text, profile_text)

    # cosine_distance = 1 - cosine_similarity, so a similarity threshold
    # becomes a max-distance filter.
    max_distance = 1 - settings.stage1_similarity_threshold
    distance = Offer.embedding.cosine_distance(profile_vector)
    stmt = (
        select(Offer)
        .where(Offer.status == OfferStatus.new, Offer.embedding.is_not(None), distance <= max_distance)
        .order_by(distance)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _build_profile_summary(profile: Profile) -> str:
    lines = [f"Summary: {profile.summary or 'N/A'}"]
    lines.append("Skills: " + ", ".join(s.name for s in profile.skills))
    for exp in profile.experiences:
        lines.append(f"Experience: {exp.title} at {exp.company} — {(exp.description or '')[:300]}")
    for edu in profile.education:
        lines.append(f"Education: {edu.degree or ''} in {edu.field_of_study or ''} at {edu.institution}")
    for cert in profile.certifications:
        lines.append(f"Certification: {cert.name} ({cert.issuer or ''})")
    return "\n".join(lines)


async def stage2_score(offer: Offer, profile: Profile) -> MatchResult:
    """Call the LLM with structured tool-use output to score one offer.

    Scoring the same offer against the same profile is deterministic enough
    to cache, and it's the only paid call in the pipeline. The key covers the
    offer description and the rendered profile summary rather than just the
    IDs, so editing either side rescores instead of returning a stale hit.
    """
    profile_text = _build_profile_summary(profile)
    offer_text = f"Title: {offer.title}\nCompany: {offer.company}\nLocation: {offer.location}\n" \
                 f"Contract: {offer.contract_type}\nDescription:\n{offer.description}"

    cache_key = build_cache_key(
        "match",
        settings.cache_prompt_version,
        str(offer.id),
        offer.description or "",
        profile_text,
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return MatchResult.model_validate_json(cached)

    payload = call_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_content=f"CANDIDATE PROFILE:\n{profile_text}\n\nOFFER:\n{offer_text}",
        tool_name="submit_match_result",
        tool_description="Submit the structured match result for this offer.",
        json_schema=MatchResult.model_json_schema(),
        max_tokens=1024,
    )
    result = MatchResult.model_validate(payload)
    await cache_set(cache_key, result.model_dump_json(), settings.match_cache_ttl_seconds)
    return result


async def score_offers(db: AsyncSession, profile: Profile, offers: list[Offer]) -> None:
    """Score each offer via stage 2 and persist the result."""
    for offer in offers:
        result = await stage2_score(offer, profile)
        offer.match_score = result.score
        offer.match_reasoning = result.reasoning
        offer.missing_skills = result.missing_skills
        offer.dealbreakers = result.dealbreakers
        offer.status = OfferStatus.scored
        db.add(offer)
    await db.commit()
