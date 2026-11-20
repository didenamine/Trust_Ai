"""Business logic for US08 (adding and listing job offers)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job_offer import JobOffer
from app.models.user import User
from app.services import offer_fetcher


def _find_by_url(db: Session, *, user: User, url: str) -> JobOffer | None:
    statement = select(JobOffer).where(JobOffer.user_id == user.id, JobOffer.source_url == url)
    return db.scalars(statement).first()


def _save(db: Session, offer: JobOffer) -> JobOffer:
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def create_text_offer(db: Session, *, user: User, text: str) -> JobOffer:
    return _save(db, JobOffer(user_id=user.id, source_type="text", content=text))


def create_url_offer(db: Session, *, user: User, url: str) -> tuple[JobOffer, bool]:
    """Save the offer found at `url`. Returns `(offer, created)`.

    A URL is saved only once per user: adding it again (even with a trailing slash or
    tracking parameters) returns the existing offer without downloading the page again.
    Raises the errors of `offer_fetcher`.
    """
    normalized = offer_fetcher.normalize_url(url)
    if existing := _find_by_url(db, user=user, url=normalized):
        return existing, False

    content = offer_fetcher.fetch_offer_text(url)
    offer = JobOffer(user_id=user.id, source_type="url", source_url=normalized, content=content)
    try:
        return _save(db, offer), True
    except IntegrityError:  # the same URL was added at the very same moment
        db.rollback()
        if existing := _find_by_url(db, user=user, url=normalized):
            return existing, False
        raise


def list_offers(db: Session, *, user: User) -> list[JobOffer]:
    statement = (
        select(JobOffer).where(JobOffer.user_id == user.id).order_by(JobOffer.created_at.desc())
    )
    return list(db.scalars(statement))
