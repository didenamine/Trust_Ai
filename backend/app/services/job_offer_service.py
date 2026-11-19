"""Business logic for US08 (adding and listing job offers)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_offer import JobOffer
from app.models.user import User


def create_text_offer(db: Session, *, user: User, text: str) -> JobOffer:
    offer = JobOffer(user_id=user.id, source_type="text", content=text)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def list_offers(db: Session, *, user: User) -> list[JobOffer]:
    statement = (
        select(JobOffer).where(JobOffer.user_id == user.id).order_by(JobOffer.created_at.desc())
    )
    return list(db.scalars(statement))
