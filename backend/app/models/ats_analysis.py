import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ATSAnalysis(Base):
    """US24 - latest ATS result for one uploaded CV version.

    A CV upload reuses the same `cv_documents.id` (US03 replaces the file in place),
    so `cv_storage_key` identifies the actual uploaded version. One row per
    (candidate, stored file): re-running the analysis updates that row, uploading a
    new CV produces an independent row. Old rows are kept but never exposed as the
    current result. There is no history endpoint in Sprint 1.
    """

    __tablename__ = "ats_analyses"
    __table_args__ = (
        UniqueConstraint("user_id", "cv_storage_key", name="uq_ats_user_cv_version"),
        Index("ix_ats_analyses_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cv_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cv_documents.id", ondelete="SET NULL"), nullable=True
    )
    cv_storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # ATSAnalysisResult (app/schemas/ats.py); never contains CV text or snippets.
    result: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    scoring_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
