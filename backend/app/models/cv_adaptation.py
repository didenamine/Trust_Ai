import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CVAdaptation(Base):
    """US14 - the latest adapted CV of a candidate for one offer (one row per pair).

    `data` holds an `AdaptedCV` (app/schemas/cv_adaptation.py) as JSON. Generating again
    for the same offer replaces the row. Unlike the offer analysis, an adaptation belongs
    to the candidate: two candidates adapting the same offer get their own result.
    """

    __tablename__ = "cv_adaptations"
    __table_args__ = (UniqueConstraint("user_id", "offer_id", name="uq_cv_adaptations_user_offer"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    # JSONB in PostgreSQL, plain JSON elsewhere (SQLite in the tests).
    data: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    # The matching score (US12) the adaptation started from, and the gap it could not fill.
    matching_score: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
