from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job_offer import UserOffer
from app.models.user import User
from app.schemas.job_offer import JobOfferCreate, JobOfferOut
from app.services import job_offer_service, offer_fetcher

router = APIRouter(tags=["offers"])


def _to_out(link: UserOffer) -> JobOfferOut:
    """An offer as seen by one user: `created_at` is when *this* user added it."""
    offer = link.offer
    return JobOfferOut(
        id=offer.id,
        source_type=offer.source_type,
        source_url=offer.source_url,
        content=offer.content,
        created_at=link.created_at,
    )


@router.post(
    "",
    response_model=JobOfferOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_200_OK: {"description": "Offer already in your list."}},
)
def create_offer(
    payload: JobOfferCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobOfferOut:
    if payload.text is not None:
        link = job_offer_service.create_text_offer(db, user=current_user, text=payload.text)
        return _to_out(link)

    try:
        link, added = job_offer_service.create_url_offer(
            db, user=current_user, url=str(payload.url)
        )
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

    if not added:
        response.status_code = status.HTTP_200_OK
    return _to_out(link)


@router.get("", response_model=list[JobOfferOut])
def list_my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobOfferOut]:
    return [_to_out(link) for link in job_offer_service.list_offers(db, user=current_user)]
