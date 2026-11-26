import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class JobOffer(Base):
    """A job offer, pasted as text or fetched from a URL (US08).

    A URL offer is stored once and shared by every candidate who added that URL; a pasted
    text offer belongs to a single candidate. Who owns what is stored in `UserOffer`.
    """

    __tablename__ = "job_offers"
    __table_args__ = (UniqueConstraint("source_url", name="uq_job_offers_source_url"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "text" or "url"
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserOffer(Base):
    """An offer in a candidate's list (the link between a user and a job offer)."""

    __tablename__ = "user_offers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_offers.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    offer: Mapped[JobOffer] = relationship(lazy="joined")
