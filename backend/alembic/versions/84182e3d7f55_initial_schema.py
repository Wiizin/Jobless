"""initial schema

Revision ID: 84182e3d7f55
Revises:
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "84182e3d7f55"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384  # must match app.config.Settings.embedding_dim


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    offer_status = postgresql.ENUM("new", "scored", "reviewed", "dismissed", name="offerstatus")
    document_type = postgresql.ENUM("cv", "cover_letter", "qa", name="documenttype")
    document_status = postgresql.ENUM("pending_review", "approved", name="documentstatus")
    application_status = postgresql.ENUM(
        "not_applied", "applied", "interviewing", "rejected", "offer_received", "withdrawn",
        name="applicationstatus",
    )
    bind = op.get_bind()
    offer_status.create(bind, checkfirst=True)
    document_type.create(bind, checkfirst=True)
    document_status.create(bind, checkfirst=True)
    application_status.create(bind, checkfirst=True)

    op.create_table(
        "profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("links", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bullets", sa.JSON(), nullable=False, server_default="[]"),
    )

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("proficiency", sa.String(50), nullable=True),
    )

    op.create_table(
        "education",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("degree", sa.String(255), nullable=True),
        sa.Column("field_of_study", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("credential_url", sa.String(1024), nullable=True),
    )

    op.create_table(
        "search_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="default"),
        sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("locations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("contract_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("target_companies", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("min_score_threshold", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("contract_type", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("posted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_reasoning", sa.Text(), nullable=True),
        sa.Column("missing_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("dealbreakers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", offer_status, nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "external_id", name="uq_offers_source_external_id"),
    )
    op.create_index("ix_offers_status", "offers", ["status"])
    op.create_index(
        "ix_offers_embedding_cosine",
        "offers",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": "100"},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", document_type, nullable=False),
        sa.Column("selected_experiences", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("bullets", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("cover_letter_sections", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("qa_answers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("status", document_status, nullable=False, server_default="pending_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", application_status, nullable=False, server_default="not_applied"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("documents")
    op.drop_index("ix_offers_embedding_cosine", table_name="offers")
    op.drop_index("ix_offers_status", table_name="offers")
    op.drop_table("offers")
    op.drop_table("search_profile")
    op.drop_table("certifications")
    op.drop_table("education")
    op.drop_table("skills")
    op.drop_table("experiences")
    op.drop_table("profile")

    bind = op.get_bind()
    postgresql.ENUM(name="applicationstatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="documentstatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="documenttype").drop(bind, checkfirst=True)
    postgresql.ENUM(name="offerstatus").drop(bind, checkfirst=True)
