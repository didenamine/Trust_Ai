from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job_offer import JobOffer
from app.models.user import User
from app.schemas.job_offer import JobOfferCreate, JobOfferOut
from app.services import job_offer_service, offer_fetcher

router = APIRouter(tags=["offers"])


@router.post("", response_model=JobOfferOut, status_code=status.HTTP_201_CREATED)
def create_offer(
    payload: JobOfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobOffer:
    if payload.text is not None:
        return job_offer_service.create_text_offer(db, user=current_user, text=payload.text)

    try:
        return job_offer_service.create_url_offer(db, user=current_user, url=str(payload.url))
    except offer_fetcher.UnsafeUrlError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Cette adresse n'est pas autorisée."
        ) from exc
    except offer_fetcher.NoContentError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"{exc} Collez plutôt le texte de l'offre.",
        ) from exc
    except offer_fetcher.FetchFailedError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("", response_model=list[JobOfferOut])
def list_my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobOffer]:
    return job_offer_service.list_offers(db, user=current_user)
