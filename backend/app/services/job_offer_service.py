"""Business logic for US08 (adding and listing job offers)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job_offer import JobOffer, UserOffer
from app.models.user import User
from app.services import offer_fetcher


def _find_by_url(db: Session, url: str) -> JobOffer | None:
    return db.scalars(select(JobOffer).where(JobOffer.source_url == url)).first()


def _get_or_create_url_offer(db: Session, *, url: str, normalized: str) -> JobOffer:
    """The stored offer for this URL; the page is downloaded only if nobody added it yet."""
    if existing := _find_by_url(db, normalized):
        return existing

    content = offer_fetcher.fetch_offer_text(url)
    offer = JobOffer(source_type="url", source_url=normalized, content=content)
    try:
        db.add(offer)
        db.commit()
    except IntegrityError:  # someone added the same URL at the very same moment
        db.rollback()
        if existing := _find_by_url(db, normalized):
            return existing
        raise
    db.refresh(offer)
    return offer


def _attach(db: Session, *, user: User, offer: JobOffer) -> tuple[UserOffer, bool]:
    """Put `offer` in the user's list. Returns `(link, added)`; `added` is False if it was there."""
    if existing := db.get(UserOffer, (user.id, offer.id)):
        return existing, False

    link = UserOffer(user_id=user.id, offer_id=offer.id)
    try:
        db.add(link)
        db.commit()
    except IntegrityError:  # added twice at the very same moment
        db.rollback()
        if existing := db.get(UserOffer, (user.id, offer.id)):
            return existing, False
        raise
    db.refresh(link)
    return link, True


def create_text_offer(db: Session, *, user: User, text: str) -> UserOffer:
    offer = JobOffer(source_type="text", content=text)
    link = UserOffer(user_id=user.id, offer=offer)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def create_url_offer(db: Session, *, user: User, url: str) -> tuple[UserOffer, bool]:
    """Add the offer found at `url` to the user's list. Returns `(link, added)`.

    A URL is stored only once: if another candidate already added it (even with a trailing
    slash or tracking parameters), the stored offer is attached to this user and the page
    is not downloaded again. Raises the errors of `offer_fetcher`.
    """
    normalized = offer_fetcher.normalize_url(url)
    offer = _get_or_create_url_offer(db, url=url, normalized=normalized)
    return _attach(db, user=user, offer=offer)


def list_offers(db: Session, *, user: User) -> list[UserOffer]:
    statement = (
        select(UserOffer).where(UserOffer.user_id == user.id).order_by(UserOffer.created_at.desc())
    )
    return list(db.scalars(statement))
