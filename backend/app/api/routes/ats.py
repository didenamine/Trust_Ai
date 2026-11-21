import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ats import ATSAnalysisOut
from app.services import ats_analysis_service
from app.services.cv_text import CVTextError, NoTextInCVError
from app.services.llm import (
    LLMClient,
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseError,
    LLMUnavailableError,
    get_llm_client,
)
from app.services.storage import FileStorage, get_storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ats"])

_NO_CV = HTTPException(status.HTTP_404_NOT_FOUND, "Aucun CV importé")
_NO_ANALYSIS = HTTPException(status.HTTP_404_NOT_FOUND, "Ce CV n'a pas encore d'analyse ATS")


@router.get("/me", response_model=ATSAnalysisOut)
def get_my_ats_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ATSAnalysisOut:
    """Return the ATS result for the currently uploaded CV, if one exists."""
    try:
        record = ats_analysis_service.get_current_analysis(db, user_id=current_user.id)
    except ats_analysis_service.NoCVError as exc:
        raise _NO_CV from exc
    except ats_analysis_service.NoAnalysisError as exc:
        raise _NO_ANALYSIS from exc
    return ATSAnalysisOut.from_record(record)


@router.post("/me/analyze", response_model=ATSAnalysisOut)
def analyze_my_cv_for_ats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
    llm: LLMClient = Depends(get_llm_client),
) -> ATSAnalysisOut:
    """US24: analyse the imported CV with ATS criteria and save the result.

    Manual action only. Takes one LLM call, a few seconds.
    """
    try:
        record = ats_analysis_service.analyze_current_cv(db, storage, llm, user_id=current_user.id)
    except ats_analysis_service.NoCVError as exc:
        raise _NO_CV from exc
    except NoTextInCVError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Aucun texte n'a pu être lu dans ce CV (document scanné ou image ?). "
            "Importez un PDF ou un DOCX contenant du texte",
        ) from exc
    except CVTextError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Le fichier du CV est illisible"
        ) from exc
    except ats_analysis_service.UnsupportedCVLanguageError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Langue du CV non prise en charge : le CV doit être en français ou en anglais",
        ) from exc
    except LLMNotConfiguredError as exc:
        logger.error("ATS analysis: LLM not configured: %s", exc)
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
        logger.warning("ATS analysis: LLM unavailable: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Le service d'analyse est momentanément indisponible, réessayez plus tard",
        ) from exc
    except LLMResponseError as exc:
        # Never log the CV itself: only the error summary.
        logger.error("ATS analysis: unusable LLM answer: %s", exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "L'analyse ATS du CV a échoué, veuillez réessayer"
        ) from exc

    return ATSAnalysisOut.from_record(record)
