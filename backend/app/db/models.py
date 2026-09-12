"""SQLAlchemy 2.0 ORM models.

Tables: profile, experiences, skills, education, certifications,
search_profile, offers, documents, applications.

`education` and `certifications` are broken out from `profile` because the
app description calls them out as first-class profile content even though
the folder-structure doc only named "skills, experiences" explicitly —
kept here so generation.py has real rows to select from instead of a
catch-all JSON blob.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings

settings = get_settings()


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class Profile(TimestampMixin, Base):
    """Single master profile. The app is single-user, so in practice one row."""

    __tablename__ = "profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    links: Mapped[dict] = mapped_column(JSON, default=dict)  # {"linkedin": "...", "github": "...", "portfolio": "..."}

    experiences: Mapped[list["Experience"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    education: Mapped[list["Education"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    search_profiles: Mapped[list["SearchProfile"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bullets: Mapped[list[str]] = mapped_column(JSON, default=list)  # raw achievement bullets, never fabricated on top

    profile: Mapped["Profile"] = relationship(back_populates="experiences")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "language", "framework", "tool"
    proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "beginner"/"intermediate"/"expert"

    profile: Mapped["Profile"] = relationship(back_populates="skills")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    institution: Mapped[str] = mapped_column(String(255))
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="education")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="certifications")


class SearchProfile(TimestampMixin, Base):
    """Keywords/location/contract-type/company config driving offer collection."""

    __tablename__ = "search_profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(255), default="default")
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    contract_types: Mapped[list[str]] = mapped_column(JSON, default=list)  # e.g. "internship", "full-time"
    target_companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_score_threshold: Mapped[int] = mapped_column(Integer, default=50)
    is_active: Mapped[bool] = mapped_column(default=True)

    profile: Mapped["Profile"] = relationship(back_populates="search_profiles")


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------


class OfferStatus(str, enum.Enum):
    new = "new"
    scored = "scored"
    reviewed = "reviewed"
    dismissed = "dismissed"


class Offer(TimestampMixin, Base):
    __tablename__ = "offers"
    __table_args__ = ()

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)

    source: Mapped[str] = mapped_column(String(50))  # "agency_api" | "aggregator_api" | "ats_boards" | "manual"
    external_id: Mapped[str] = mapped_column(String(255))

    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(2048))
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim), nullable=True)

    # Stage 2 (Claude) match results — see schemas/match.py::MatchResult
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    dealbreakers: Mapped[list[str]] = mapped_column(JSON, default=list)

    status: Mapped[OfferStatus] = mapped_column(Enum(OfferStatus), default=OfferStatus.new)

    documents: Mapped[list["Document"]] = relationship(back_populates="offer", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="offer", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Generated documents
# ---------------------------------------------------------------------------


class DocumentType(str, enum.Enum):
    cv = "cv"
    cover_letter = "cover_letter"
    qa = "qa"


class DocumentStatus(str, enum.Enum):
    pending_review = "pending_review"
    approved = "approved"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"))
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))

    # Structured content — see schemas/document.py::GeneratedDocument. Content here
    # only ever references experience/skill rows that already exist in the profile.
    selected_experiences: Mapped[list[str]] = mapped_column(JSON, default=list)  # experience UUIDs (as str)
    bullets: Mapped[list[str]] = mapped_column(JSON, default=list)
    cover_letter_sections: Mapped[dict] = mapped_column(JSON, default=dict)  # {intro, body_paragraphs, closing}
    qa_answers: Mapped[dict] = mapped_column(JSON, default=dict)  # {question: answer}

    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # rendered docx path, set on approval
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.pending_review)

    offer: Mapped["Offer"] = relationship(back_populates="documents")
    applications: Mapped[list["Application"]] = relationship(back_populates="document")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------


class ApplicationStatus(str, enum.Enum):
    not_applied = "not_applied"
    applied = "applied"
    interviewing = "interviewing"
    rejected = "rejected"
    offer_received = "offer_received"
    withdrawn = "withdrawn"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.not_applied)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    offer: Mapped["Offer"] = relationship(back_populates="applications")
    document: Mapped["Document | None"] = relationship(back_populates="applications")
