import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Profile(Base):
    """A candidate's structured profile (T-09). One per candidate.

    `data` holds a `CandidateProfile` (app/schemas/profile.py) as JSON. Always go through
    `profile_service` to read or write it, so the JSON is validated against the schema.
    """

    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # JSONB in PostgreSQL, plain JSON elsewhere (SQLite in the tests).
    data: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    """How the profile was first created: "cv_analysis" (US05) or "manual" (US06)."""
    cv_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cv_documents.id", ondelete="SET NULL"), nullable=True
    )
    """The imported CV the profile was extracted from (US05), if any."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
