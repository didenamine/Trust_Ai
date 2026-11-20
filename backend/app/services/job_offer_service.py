"""Business logic for US08 (adding and listing job offers)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_offer import JobOffer
from app.models.user import User
from app.services import offer_fetcher


def _save(db: Session, offer: JobOffer) -> JobOffer:
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def create_text_offer(db: Session, *, user: User, text: str) -> JobOffer:
    return _save(db, JobOffer(user_id=user.id, source_type="text", content=text))


def create_url_offer(db: Session, *, user: User, url: str) -> JobOffer:
    """Fetch the page at `url`, then save its text. Raises the errors of `offer_fetcher`."""
    content = offer_fetcher.fetch_offer_text(url)
    return _save(db, JobOffer(user_id=user.id, source_type="url", source_url=url, content=content))


def list_offers(db: Session, *, user: User) -> list[JobOffer]:
    statement = (
        select(JobOffer).where(JobOffer.user_id == user.id).order_by(JobOffer.created_at.desc())
    )
    return list(db.scalars(statement))
