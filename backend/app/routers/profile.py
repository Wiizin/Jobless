"""Profile + search-profile CRUD."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
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
