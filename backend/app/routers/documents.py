"""Generate → human-review/edit → approve → download.

Every generated document is created with status=pending_review and stays
that way until an explicit /approve call. Rendering to a downloadable file
only happens on approval, and downloading a non-approved document is
rejected. Nothing in this router sends or submits content anywhere.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_session_token
from app.db.models import Document, DocumentStatus, DocumentType, Offer, Profile
from app.db.session import get_db
from app.schemas.document import DocumentEditRequest, DocumentOut, GenerateDocumentRequest
from app.services import docgen, generation

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(verify_session_token)])


async def _load_offer(db: AsyncSession, offer_id: uuid.UUID) -> Offer:
    offer = await db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


async def _load_profile_full(db: AsyncSession, profile_id: uuid.UUID) -> Profile:
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


async def _load_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/generate", response_model=DocumentOut, status_code=201)
async def generate(
    payload: GenerateDocumentRequest,
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Document:
    offer = await _load_offer(db, payload.offer_id)
    profile = await _load_profile_full(db, profile_id)

    generated = await generation.generate_document(offer, profile)

    document = Document(
        offer_id=offer.id,
        profile_id=profile.id,
        doc_type=DocumentType(payload.doc_type),
        selected_experiences=[str(eid) for eid in generated.selected_experiences],
        bullets=generated.bullets,
        cover_letter_sections=generated.cover_letter_sections.model_dump() if generated.cover_letter_sections else {},
        qa_answers=generated.qa_answers,
        status=DocumentStatus.pending_review,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Document:
    return await _load_document(db, document_id)


@router.patch("/{document_id}", response_model=DocumentOut)
async def edit_document(document_id: uuid.UUID, payload: DocumentEditRequest, db: AsyncSession = Depends(get_db)) -> Document:
    """Human edits before approval. Stays in pending_review."""
    document = await _load_document(db, document_id)
    if document.status == DocumentStatus.approved:
        raise HTTPException(status_code=409, detail="Approved documents are immutable; generate a new one instead")

    if payload.selected_experiences is not None:
        document.selected_experiences = [str(eid) for eid in payload.selected_experiences]
    if payload.bullets is not None:
        document.bullets = payload.bullets
    if payload.cover_letter_sections is not None:
        document.cover_letter_sections = payload.cover_letter_sections.model_dump()
    if payload.qa_answers is not None:
        document.qa_answers = payload.qa_answers

    await db.commit()
    await db.refresh(document)
    return document


@router.post("/{document_id}/approve", response_model=DocumentOut)
async def approve_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Document:
    """Human approval gate — the only place a file gets rendered to disk."""
    document = await _load_document(db, document_id)
    offer = await _load_offer(db, document.offer_id)
    profile = await _load_profile_full(db, document.profile_id)

    if document.doc_type == DocumentType.cv:
        path = docgen.render_cv(profile, offer, document, profile.experiences)
    elif document.doc_type == DocumentType.cover_letter:
        path = docgen.render_cover_letter(profile, offer, document)
    else:
        path = None  # Q&A content has no standalone file; reviewed in-app.

    document.file_path = path
    document.status = DocumentStatus.approved
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/{document_id}/download")
async def download_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> FileResponse:
    document = await _load_document(db, document_id)
    if document.status != DocumentStatus.approved or not document.file_path:
        raise HTTPException(status_code=409, detail="Document must be approved and rendered before download")
    return FileResponse(document.file_path, filename=document.file_path.split("/")[-1])
