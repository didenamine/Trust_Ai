"""US14 - Adaptation du CV à une offre sélectionnée."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cv_adaptation import CVAdaptationOut
from app.services import cv_adaptation_service, offer_analysis_service
from app.services.llm import (
    LLMClient,
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    get_llm_client,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["adaptations"])

_NO_PROFILE = (
    "Profil candidat introuvable. Importez votre CV ou remplissez votre profil "
    "avant d'adapter votre CV."
)


@router.get("/{offer_id}", response_model=CVAdaptationOut)
def get_cv_adaptation(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CVAdaptationOut:
    """US14: return the stored adaptation of the candidate's CV for this offer."""
    try:
        record = cv_adaptation_service.get_adaptation(
            db, user_id=current_user.id, offer_id=offer_id
        )
        if record is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune adaptation pour cette offre.")
        return cv_adaptation_service.to_output(db, record)
    except offer_analysis_service.OfferNotInListError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable.") from exc
    except cv_adaptation_service.NoProfileError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NO_PROFILE) from exc


@router.post(
    "/{offer_id}",
    response_model=CVAdaptationOut,
    status_code=status.HTTP_200_OK,
    responses={status.HTTP_201_CREATED: {"description": "First adaptation for this offer."}},
)
def adapt_my_cv(
    offer_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
) -> CVAdaptationOut:
    """US14: adapt the candidate's profile to a selected, analysed offer.

    Returns a complete, ATS-friendly CV (`document`, and the same as plain text in
    `ats_text`) based on the gap computed by the matching (US12). Calling it again
    replaces the stored result. One LLM call, a few seconds. Not verified in the MVP.
    """
    try:
        record, created = cv_adaptation_service.adapt_cv(
            db, llm, user_id=current_user.id, offer_id=offer_id
        )
        output = cv_adaptation_service.to_output(db, record)
    except offer_analysis_service.OfferNotInListError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offre introuvable.") from exc
    except cv_adaptation_service.NoProfileError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NO_PROFILE) from exc
    except cv_adaptation_service.OfferNotAnalyzedError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cette offre n'a pas encore été analysée. Veuillez d'abord l'analyser.",
        ) from exc
    except LLMNotConfiguredError as exc:
        logger.error("CV adaptation: LLM not configured: %s", exc)
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
        logger.warning("CV adaptation: LLM unavailable: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Le service d'analyse est momentanément indisponible, réessayez plus tard",
        ) from exc
    except LLMResponseError as exc:
        # Never log the CV itself: only the error summary.
        logger.error("CV adaptation: unusable LLM answer: %s", exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "L'adaptation du CV a échoué, veuillez réessayer"
        ) from exc

    if created:
        response.status_code = status.HTTP_201_CREATED
    return output
