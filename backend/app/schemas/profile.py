"""Profile + search-profile request/response models."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr


class ExperienceIn(BaseModel):
    title: str
    company: str
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    bullets: list[str] = []


class ExperienceOut(ExperienceIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class SkillIn(BaseModel):
    name: str
    category: str | None = None
    proficiency: str | None = None


class SkillOut(SkillIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class EducationIn(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class EducationOut(EducationIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class CertificationIn(BaseModel):
    name: str
    issuer: str | None = None
    issued_date: date | None = None
    expiry_date: date | None = None
    credential_url: str | None = None


class CertificationOut(CertificationIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ProfileIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: dict[str, str] = {}


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    experiences: list[ExperienceOut] = []
    skills: list[SkillOut] = []
    education: list[EducationOut] = []
    certifications: list[CertificationOut] = []


class SearchProfileIn(BaseModel):
    name: str = "default"
    keywords: list[str] = []
    locations: list[str] = []
    contract_types: list[str] = []
    target_companies: list[str] = []
    min_score_threshold: int = 50
    is_active: bool = True


class SearchProfileOut(SearchProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    profile_id: uuid.UUID
