"""Profile + search-profile CRUD, plus CV-upload import.

POST /profile/import-cv is the bulk alternative to the per-item POSTs
below: one uploaded file is parsed into the same tables in one shot. See
services/cv_import.py for the extraction (and the no-fabrication rule it
has to hold to).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_session_token
from app.db.models import Certification, Education, Experience, Profile, SearchProfile, Skill
from app.db.session import get_db
from app.schemas.profile import (
    CertificationIn,
    EducationIn,
    ExperienceIn,
    ProfileIn,
    ProfileOut,
    SearchProfileIn,
    SearchProfileOut,
    SkillIn,
)
from app.services import cv_import

MAX_CV_UPLOAD_BYTES = 10 * 1024 * 1024  # ~10MB

router = APIRouter(prefix="/profile", tags=["profile"], dependencies=[Depends(verify_session_token)])


async def _load_profile(db: AsyncSession, profile_id: uuid.UUID) -> Profile:
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
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("", response_model=ProfileOut, status_code=201)
async def create_profile(payload: ProfileIn, db: AsyncSession = Depends(get_db)) -> Profile:
    profile = Profile(**payload.model_dump())
    db.add(profile)
    await db.commit()
    return await _load_profile(db, profile.id)


@router.post("/import-cv", response_model=ProfileOut, status_code=201)
async def import_cv(
    file: UploadFile = File(...),
    profile_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """Build (or re-sync) a profile from one uploaded CV.

    No intermediate review screen — the parsed result is written straight to
    the profile tables. With `profile_id`, the existing profile's
    experiences/skills/education/certifications are replaced wholesale by
    what the CV contains; without it, a new profile is created.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(cv_import.SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {', '.join(cv_import.SUPPORTED_EXTENSIONS)}",
        )

    # Starlette populates .size from the multipart parser, so oversized uploads
    # are rejected before read() pulls the whole body into memory.
    if file.size is not None and file.size > MAX_CV_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CV file too large (limit 10MB)")

    if profile_id is not None:
        await _load_profile(db, profile_id)  # 404 before spending an LLM call

    content = await file.read()
    if len(content) > MAX_CV_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CV file too large (limit 10MB)")

    try:
        raw_text = cv_import.extract_text(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parsed = cv_import.parse_cv_text(raw_text)

    try:
        return await cv_import.apply_parsed_profile(db, profile_id, parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_profile(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Profile:
    return await _load_profile(db, profile_id)


@router.put("/{profile_id}", response_model=ProfileOut)
async def update_profile(profile_id: uuid.UUID, payload: ProfileIn, db: AsyncSession = Depends(get_db)) -> Profile:
    profile = await _load_profile(db, profile_id)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    await db.commit()
    return await _load_profile(db, profile_id)


@router.post("/{profile_id}/experiences", response_model=ProfileOut, status_code=201)
async def add_experience(profile_id: uuid.UUID, payload: ExperienceIn, db: AsyncSession = Depends(get_db)) -> Profile:
    await _load_profile(db, profile_id)  # 404 if missing
    db.add(Experience(profile_id=profile_id, **payload.model_dump()))
    await db.commit()
    return await _load_profile(db, profile_id)


@router.post("/{profile_id}/skills", response_model=ProfileOut, status_code=201)
async def add_skill(profile_id: uuid.UUID, payload: SkillIn, db: AsyncSession = Depends(get_db)) -> Profile:
    await _load_profile(db, profile_id)
    db.add(Skill(profile_id=profile_id, **payload.model_dump()))
    await db.commit()
    return await _load_profile(db, profile_id)


@router.post("/{profile_id}/education", response_model=ProfileOut, status_code=201)
async def add_education(profile_id: uuid.UUID, payload: EducationIn, db: AsyncSession = Depends(get_db)) -> Profile:
    await _load_profile(db, profile_id)
    db.add(Education(profile_id=profile_id, **payload.model_dump()))
    await db.commit()
    return await _load_profile(db, profile_id)


@router.post("/{profile_id}/certifications", response_model=ProfileOut, status_code=201)
async def add_certification(
    profile_id: uuid.UUID, payload: CertificationIn, db: AsyncSession = Depends(get_db)
) -> Profile:
    await _load_profile(db, profile_id)
    db.add(Certification(profile_id=profile_id, **payload.model_dump()))
    await db.commit()
    return await _load_profile(db, profile_id)


@router.post("/{profile_id}/search-profile", response_model=SearchProfileOut, status_code=201)
async def create_search_profile(
    profile_id: uuid.UUID, payload: SearchProfileIn, db: AsyncSession = Depends(get_db)
) -> SearchProfile:
    await _load_profile(db, profile_id)
    sp = SearchProfile(profile_id=profile_id, **payload.model_dump())
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


@router.get("/{profile_id}/search-profile", response_model=list[SearchProfileOut])
async def list_search_profiles(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[SearchProfile]:
    stmt = select(SearchProfile).where(SearchProfile.profile_id == profile_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
