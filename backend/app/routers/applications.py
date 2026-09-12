"""Application status tracking — manual, user-driven updates only.

No endpoint here submits anything anywhere; the user applies manually
(optionally using a downloaded, approved document + browser autofill-assist)
and then records what happened here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_session_token
from app.db.models import Application, ApplicationStatus, DocumentStatus, Document
from app.db.session import get_db

router = APIRouter(prefix="/applications", tags=["applications"], dependencies=[Depends(verify_session_token)])


class ApplicationCreate(BaseModel):
    offer_id: uuid.UUID
    document_id: uuid.UUID | None = None
    notes: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    document_id: uuid.UUID | None
    status: str
    applied_at: datetime | None
    notes: str | None
    created_at: datetime


@router.post("", response_model=ApplicationOut, status_code=201)
async def create_application(payload: ApplicationCreate, db: AsyncSession = Depends(get_db)) -> Application:
    if payload.document_id is not None:
        document = await db.get(Document, payload.document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.status != DocumentStatus.approved:
            raise HTTPException(status_code=409, detail="Cannot attach an unapproved document to an application")

    app_row = Application(offer_id=payload.offer_id, document_id=payload.document_id, notes=payload.notes)
    db.add(app_row)
    await db.commit()
    await db.refresh(app_row)
    return app_row


@router.get("", response_model=list[ApplicationOut])
async def list_applications(db: AsyncSession = Depends(get_db)) -> list[Application]:
    result = await db.execute(select(Application).order_by(Application.created_at.desc()))
    return list(result.scalars().all())


@router.patch("/{application_id}", response_model=ApplicationOut)
async def update_application_status(
    application_id: uuid.UUID, payload: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db)
) -> Application:
    app_row = await db.get(Application, application_id)
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    app_row.status = payload.status
    if payload.notes is not None:
        app_row.notes = payload.notes
    if payload.status == ApplicationStatus.applied and app_row.applied_at is None:
        app_row.applied_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(app_row)
    return app_row
