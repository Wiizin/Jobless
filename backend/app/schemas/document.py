"""Structured output for generated CV/cover-letter/Q&A content.

generation.py must populate this ONLY from experiences/skills/education/
certifications that already exist on the profile — see hard constraint #2
in the project brief. Nothing here is free text the backend blindly trusts;
it's the exact JSON shape requested from Claude.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CoverLetterSections(BaseModel):
    intro: str
    body_paragraphs: list[str]
    closing: str


class GeneratedDocument(BaseModel):
    selected_experiences: list[uuid.UUID] = Field(
        default_factory=list, description="IDs of existing Experience rows chosen for this application."
    )
    bullets: list[str] = Field(
        default_factory=list,
        description="Rephrased/reordered bullets drawn only from the selected experiences — never invented.",
    )
    cover_letter_sections: CoverLetterSections | None = None
    qa_answers: dict[str, str] = Field(default_factory=dict)
    status: Literal["pending_review", "approved"] = "pending_review"


class GenerateDocumentRequest(BaseModel):
    offer_id: uuid.UUID
    doc_type: Literal["cv", "cover_letter", "qa"]


class DocumentEditRequest(BaseModel):
    """Human edits applied before approval — still constrained to the same shape."""

    selected_experiences: list[uuid.UUID] | None = None
    bullets: list[str] | None = None
    cover_letter_sections: CoverLetterSections | None = None
    qa_answers: dict[str, str] | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    profile_id: uuid.UUID
    doc_type: str
    selected_experiences: list[str]
    bullets: list[str]
    cover_letter_sections: dict
    qa_answers: dict
    file_path: str | None
    status: str
    created_at: datetime
