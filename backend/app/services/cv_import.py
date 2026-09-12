"""Parse an uploaded CV (PDF / DOCX / LaTeX) straight into profile tables.

This is the bulk alternative to typing experiences/skills/education/
certifications in one POST at a time (routers/profile.py). There is no
review step: what comes out of the CV *is* the profile.

That makes the no-fabrication rule load-bearing here in the same way it is
in services/generation.py. The extraction prompt is explicit that the model
may only report what is literally written in the uploaded text — a field
the CV doesn't contain comes back empty, never inferred from context, and
never filled with a plausible-looking placeholder. Nothing downstream can
tell an invented job title from a real one, so it has to not happen here.
"""
from __future__ import annotations

import io
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Certification, Education, Experience, Profile, Skill
from app.schemas.profile import ParsedProfile
from app.services.llm_client import call_structured

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".tex", ".txt")

_SYSTEM_PROMPT = """You extract a candidate's CV into structured data by calling the
`submit_parsed_profile` tool.

Extract ONLY what is explicitly written in the CV text you are given:
- contact details (full name, email, phone, location) and any links (LinkedIn,
  GitHub, portfolio, personal site) that appear in the text
- EVERY work experience, with its title, company, location, start/end dates,
  description, and achievement bullets exactly as listed
- EVERY skill mentioned, with its category/proficiency only if the CV states one
- EVERY education entry (institution, degree, field of study, dates)
- EVERY certification (name, issuer, dates, credential URL)

Rules you must not break:
- If a field is not present in the text, leave it out or leave it empty. Do NOT
  infer it, do NOT guess it from context, and do NOT substitute a plausible
  value. An empty field is a correct answer; an invented one is not.
- Do not embellish, summarize into achievements that aren't stated, reword
  responsibilities into stronger claims, or add skills implied by a job title
  but not actually listed.
- Copy the candidate's own wording for descriptions and bullets.
- Dates go in ISO format (YYYY-MM-DD). When the CV gives only a month and year,
  use the 1st of that month; when it gives only a year, use January 1st of that
  year. If no date is given at all, leave it empty rather than estimating one.
- The source may be raw LaTeX. Read through the markup to the content; never
  emit LaTeX commands as if they were profile data."""


def extract_text(filename: str, content: bytes) -> str:
    """Pull plain text out of an uploaded CV, dispatching on extension.

    Parser libraries are imported lazily so this module stays importable
    (and testable) in an environment that only has one of them installed.
    """
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx"):
        from docx import Document as DocxDocument

        document = DocxDocument(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    if name.endswith((".tex", ".txt")):
        # LaTeX source goes to the model as-is — it reads past the markup, and
        # stripping commands here would risk dropping real content.
        return content.decode("utf-8", errors="replace")

    raise ValueError(
        f"Unsupported CV file type: {filename!r}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def parse_cv_text(raw_text: str) -> ParsedProfile:
    """Run the extraction prompt over CV text and return the structured result."""
    payload = call_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_content=f"CV TEXT:\n{raw_text}",
        tool_name="submit_parsed_profile",
        tool_description="Submit the profile data extracted verbatim from the CV.",
        json_schema=ParsedProfile.model_json_schema(),
        max_tokens=4096,
    )
    return ParsedProfile.model_validate(payload)


def _nonempty(value):
    """True for a value the CV actually yielded (not None, not blank/empty)."""
    if value is None:
        return False
    if isinstance(value, (str, dict, list)):
        return bool(value)
    return True


async def apply_parsed_profile(
    db: AsyncSession, profile_id: uuid.UUID | None, parsed: ParsedProfile
) -> Profile:
    """Write a ParsedProfile into the profile tables.

    Children (experiences/skills/education/certifications) are a full
    re-sync, not a merge: re-uploading a CV replaces them outright, which is
    how the user edits their profile. Top-level fields are only overwritten
    where the CV actually supplied something, so a re-upload of a CV that
    omits e.g. a phone number doesn't blank out one already stored.
    """
    if profile_id is None:
        # full_name and email are NOT NULL on Profile, and this module is not
        # allowed to invent either one.
        missing = [
            field
            for field in ("full_name", "email")
            if not _nonempty(getattr(parsed, field))
        ]
        if missing:
            raise ValueError(
                "Could not create a profile from this CV: no "
                + " or ".join(missing)
                + " found in the uploaded file. Add it to the CV and re-upload, or "
                "create the profile first and pass profile_id to import into it."
            )

        profile = Profile(
            full_name=parsed.full_name,
            email=parsed.email,
            phone=parsed.phone,
            location=parsed.location,
            summary=parsed.summary,
            links=parsed.links or {},
        )
        db.add(profile)
        await db.flush()  # assign profile.id before inserting children
    else:
        profile = await db.get(Profile, profile_id)
        if profile is None:
            raise ValueError(f"Profile {profile_id} not found")

        for field in ("full_name", "email", "phone", "location", "summary", "links"):
            value = getattr(parsed, field)
            if _nonempty(value):
                setattr(profile, field, value)

    for model in (Experience, Skill, Education, Certification):
        await db.execute(delete(model).where(model.profile_id == profile.id))

    for experience in parsed.experiences:
        db.add(Experience(profile_id=profile.id, **experience.model_dump()))
    for skill in parsed.skills:
        db.add(Skill(profile_id=profile.id, **skill.model_dump()))
    for education in parsed.education:
        db.add(Education(profile_id=profile.id, **education.model_dump()))
    for certification in parsed.certifications:
        db.add(Certification(profile_id=profile.id, **certification.model_dump()))

    await db.commit()

    # The bulk deletes above bypass the ORM's identity map, so expire the
    # instance and re-select with the relationships eager-loaded (same shape
    # as routers/profile.py::_load_profile) before handing it back.
    db.expire(profile)
    stmt = (
        select(Profile)
        .where(Profile.id == profile.id)
        .options(
            selectinload(Profile.experiences),
            selectinload(Profile.skills),
            selectinload(Profile.education),
            selectinload(Profile.certifications),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()
