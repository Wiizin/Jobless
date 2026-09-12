"""Two-stage offer matching.

Stage 1: cheap cosine-similarity filter via pgvector — drops offers whose
embedding is far from the profile's embedding before any LLM call happens.

Stage 2: Claude scores only what survives stage 1 and returns a structured
MatchResult (schemas/match.py) — never free text.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Offer, OfferStatus, Profile
from app.schemas.match import MatchResult
from app.services.embeddings import embed_text, offer_embedding_text, profile_embedding_text

settings = get_settings()

_SYSTEM_PROMPT = """You score how well a job/internship offer matches a candidate's profile.
Respond ONLY by calling the `submit_match_result` tool with a score (0-100), a short
grounded reasoning, a list of missing_skills the offer requires that the profile lacks,
and a list of dealbreakers (hard mismatches like required work authorization, seniority
mismatch, or incompatible location/contract type). Base every claim strictly on the
profile and offer text provided — never assume unstated candidate qualifications."""

_TOOL_SCHEMA = {
    "name": "submit_match_result",
    "description": "Submit the structured match result for this offer.",
    "input_schema": MatchResult.model_json_schema(),
}


async def stage1_filter(
    db: AsyncSession, profile: Profile, limit: int = 200
) -> list[Offer]:
    """Cosine-similarity filter (pgvector `<=>` = cosine distance) against
    offers that haven't been scored yet."""
    skills = [s.name for s in profile.skills]
    titles = [e.title for e in profile.experiences]
    profile_text = profile_embedding_text(profile.summary or "", skills, titles)
    profile_vector = embed_text(profile_text)

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
    """Call Claude with structured tool-use output to score one offer."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    profile_text = _build_profile_summary(profile)
    offer_text = f"Title: {offer.title}\nCompany: {offer.company}\nLocation: {offer.location}\n" \
                 f"Contract: {offer.contract_type}\nDescription:\n{offer.description}"

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_match_result"},
        messages=[
            {
                "role": "user",
                "content": f"CANDIDATE PROFILE:\n{profile_text}\n\nOFFER:\n{offer_text}",
            }
        ],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "submit_match_result":
            return MatchResult.model_validate(block.input)

    raise RuntimeError("Claude did not return a submit_match_result tool call")


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
