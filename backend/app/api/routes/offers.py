import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job_offer import UserOffer
from app.models.offer_analysis import OfferAnalysis
from app.models.user import User
from app.schemas.job_offer import JobOfferCreate, JobOfferOut, JobOfferSummary
from app.schemas.offer_analysis import OfferAnalysisOut, OfferRequirements
from app.services import job_offer_service, offer_analysis_service, offer_fetcher
from app.services.llm import (
    LLMClient,
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    get_llm_client,
)
from app.services.offer_text import split_title_and_description

logger = logging.getLogger(__name__)
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


def _to_summary(link: UserOffer) -> JobOfferSummary:
    offer = link.offer
    title, description = split_title_and_description(offer.content)
    return JobOfferSummary(
        id=offer.id,
        source_type=offer.source_type,
        source_url=offer.source_url,
        title=title,
        description=description,
        created_at=link.created_at,
    )


def _to_analysis_out(analysis: OfferAnalysis) -> OfferAnalysisOut:
    return OfferAnalysisOut(
        id=analysis.id,
        offer_id=analysis.offer_id,
        requirements=OfferRequirements.model_validate(analysis.data),
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
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


@router.get("", response_model=list[JobOfferSummary])
def list_my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobOfferSummary]:
    return [_to_summary(link) for link in job_offer_service.list_offers(db, user=current_user)]


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_offer(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not job_offer_service.delete_offer(db, user=current_user, offer_id=offer_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable.")


@router.get("/{offer_id}/analysis", response_model=OfferAnalysisOut)
def get_offer_analysis(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OfferAnalysisOut:
    """US09: return the stored analysis of one of the candidate's offers."""
    try:
        analysis = offer_analysis_service.get_analysis(
            db, offer_id=offer_id, user_id=current_user.id
        )
    except offer_analysis_service.OfferNotInListError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable.") from exc
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analyse introuvable.")
    return _to_analysis_out(analysis)


@router.post(
    "/{offer_id}/analyze",
    response_model=OfferAnalysisOut,
    status_code=status.HTTP_200_OK,
    responses={status.HTTP_201_CREATED: {"description": "First analysis of this offer."}},
)
def analyze_my_offer(
    offer_id: uuid.UUID,
    response: Response,
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
) -> OfferAnalysisOut:
    """US09: analyse a saved offer, or return the cached result.

    `?refresh=true` re-runs the LLM and replaces the stored analysis. Takes a few
    seconds on the first run (one LLM call).
    """
    try:
        analysis, created = offer_analysis_service.analyze_offer(
            db, llm, offer_id=offer_id, user_id=current_user.id, refresh=refresh
        )
    except offer_analysis_service.OfferNotInListError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable.") from exc
    except offer_analysis_service.UnsupportedOfferLanguageError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Langue de l'offre non prise en charge : l'offre doit être en français ou en anglais",
        ) from exc
    except LLMNotConfiguredError as exc:
        logger.error("Offer analysis: LLM not configured: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Le service d'analyse n'est pas configuré"
        ) from exc
    except LLMRateLimitError as exc:
        retry_after = round(exc.retry_after) if exc.retry_after else 60
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop d'analyses en peu de temps, réessayez dans une minute",
            headers={"Retry-After": str(retry_after)},
        ) from exc
    except LLMUnavailableError as exc:
        logger.warning("Offer analysis: LLM unavailable: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Le service d'analyse est momentanément indisponible, réessayez plus tard",
        ) from exc
    except LLMResponseError as exc:
        # Never log the offer itself: only the error (Groq's message, validation summary).
        logger.error("Offer analysis: unusable LLM answer: %s", exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "L'analyse de l'offre a échoué, veuillez réessayer"
        ) from exc

    if created:
        response.status_code = status.HTTP_201_CREATED
    return _to_analysis_out(analysis)
