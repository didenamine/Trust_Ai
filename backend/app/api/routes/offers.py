from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job_offer import JobOffer
from app.models.user import User
from app.schemas.job_offer import JobOfferCreate, JobOfferOut
from app.services import job_offer_service

router = APIRouter(tags=["offers"])


@router.post("", response_model=JobOfferOut, status_code=status.HTTP_201_CREATED)
def create_offer(
    payload: JobOfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobOffer:
    return job_offer_service.create_text_offer(db, user=current_user, text=payload.text)


@router.get("", response_model=list[JobOfferOut])
def list_my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobOffer]:
    return job_offer_service.list_offers(db, user=current_user)
