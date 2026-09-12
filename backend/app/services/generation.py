"""Claude-driven generation of tailored CV emphasis / cover letter / Q&A content.

HARD CONSTRAINT: this module must never invent profile content. The prompt
enumerates the candidate's actual experiences/skills/education/certifications
with stable IDs, and Claude is instructed to only select, reorder and
rephrase from that list. `_validate_no_fabrication` then checks the
returned experience IDs against what was actually offered before anything
is persisted — if Claude references an ID that wasn't in the prompt, the
generation is rejected rather than silently trusted.

Every offer requirement not covered by the profile must show up in
`missing_skills` (see MatchResult from stage-2 matching) instead of being
papered over here.
"""
from __future__ import annotations

import uuid

from app.config import get_settings
from app.db.models import Offer, Profile
from app.schemas.document import GeneratedDocument

settings = get_settings()

_SYSTEM_PROMPT = """You draft tailored application content for one specific job offer, using ONLY
the candidate's real profile data provided below. You may select which existing experiences to
feature, reorder them, and rephrase their existing bullets/descriptions for tone and relevance —
you may NEVER invent a skill, employer, title, achievement, metric, or credential that is not
already present in the supplied profile. If the offer wants something the profile doesn't have,
leave it out; that gap is tracked elsewhere, not papered over here.

Respond ONLY by calling the `submit_generated_document` tool."""


def _tool_schema() -> dict:
    schema = GeneratedDocument.model_json_schema()
    return {
        "name": "submit_generated_document",
        "description": "Submit the structured generated application content.",
        "input_schema": schema,
    }


def _profile_catalog(profile: Profile) -> tuple[str, set[uuid.UUID]]:
    """Render the profile's real content with stable IDs, and return the set
    of valid experience IDs Claude is allowed to reference."""
    lines = [f"Name: {profile.full_name}", f"Summary: {profile.summary or 'N/A'}"]
    lines.append("Skills: " + ", ".join(s.name for s in profile.skills))

    valid_ids: set[uuid.UUID] = set()
    lines.append("Experiences (reference by id, do not alter facts):")
    for exp in profile.experiences:
        valid_ids.add(exp.id)
        bullets = "; ".join(exp.bullets) if exp.bullets else (exp.description or "")
        lines.append(f"- id={exp.id} | {exp.title} at {exp.company} ({exp.location or ''}): {bullets}")

    lines.append("Education:")
    for edu in profile.education:
        lines.append(f"- {edu.degree or ''} in {edu.field_of_study or ''}, {edu.institution}")

    lines.append("Certifications:")
    for cert in profile.certifications:
        lines.append(f"- {cert.name} ({cert.issuer or ''})")

    return "\n".join(lines), valid_ids


def _validate_no_fabrication(doc: GeneratedDocument, valid_experience_ids: set[uuid.UUID]) -> GeneratedDocument:
    """Drop any experience reference that wasn't actually in the profile,
    rather than trusting the model's output blindly."""
    filtered = [eid for eid in doc.selected_experiences if eid in valid_experience_ids]
    doc.selected_experiences = filtered
    return doc


async def generate_document(offer: Offer, profile: Profile) -> GeneratedDocument:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    profile_catalog, valid_ids = _profile_catalog(profile)
    offer_text = (
        f"Title: {offer.title}\nCompany: {offer.company}\nLocation: {offer.location}\n"
        f"Contract: {offer.contract_type}\nDescription:\n{offer.description}"
    )
    missing = ", ".join(offer.missing_skills) if offer.missing_skills else "none flagged"

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        tools=[_tool_schema()],
        tool_choice={"type": "tool", "name": "submit_generated_document"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"CANDIDATE PROFILE (only source of truth):\n{profile_catalog}\n\n"
                    f"OFFER:\n{offer_text}\n\n"
                    f"Known missing skills (do not claim these): {missing}"
                ),
            }
        ],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "submit_generated_document":
            doc = GeneratedDocument.model_validate(block.input)
            return _validate_no_fabrication(doc, valid_ids)

    raise RuntimeError("Claude did not return a submit_generated_document tool call")
