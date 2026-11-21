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


class OfferAnalysis(Base):
    """US09: the latest structured analysis of a job offer (one row per offer).

    `data` holds an `OfferRequirements` (app/schemas/offer_analysis.py) as JSON.
    A URL offer can be shared by several users, so the analysis belongs to the
    offer itself, not to a user; access is guarded by the `user_offers` link.
    """

    __tablename__ = "offer_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_offers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # JSONB in PostgreSQL, plain JSON elsewhere (SQLite in the tests).
    data: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
