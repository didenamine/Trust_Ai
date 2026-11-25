"""US12 & US13 - Matching API endpoints.

Computes the compatibility score and explanations between the authenticated
candidate's profile and an analysed job offer.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.matching import MatchingResult
from app.schemas.offer_analysis import OfferRequirements
from app.schemas.skill_gap import SkillGapResult
from app.services import profile_service, skill_gap_service
from app.services.matching_service import calculate_matching

router = APIRouter(tags=["matching"])

_NO_PROFILE = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Profil candidat introuvable. Veuillez créer votre profil avant de lancer le matching.",
)


# Registered before "/{offer_id}" so this literal path isn't swallowed by it.
@router.get(
    "/skill-gaps",
    response_model=SkillGapResult,
    summary="Prioritised skill gaps across every analysed offer (US33)",
)
def get_skill_gaps(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SkillGapResult:
    """Aggregate the missing skills (US12) across all of the candidate's analysed offers."""
    profile = profile_service.get_candidate_profile(db, current_user.id)
    if profile is None:
        raise _NO_PROFILE

    return skill_gap_service.compute_skill_gaps(db, user_id=current_user.id, profile=profile)


@router.get(
    "/{offer_id}",
    response_model=MatchingResult,
    summary="Get compatibility score and matching explanation for an offer (US12, US13)",
)
def get_offer_matching(
    offer_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MatchingResult:
    """Compare the candidate's profile to the analysed job offer requirements."""
    from app.services import offer_analysis_service

    profile = profile_service.get_candidate_profile(db, current_user.id)
    if profile is None:
        raise _NO_PROFILE

    try:
        analysis = offer_analysis_service.get_analysis(
            db, offer_id=offer_id, user_id=current_user.id
        )
    except offer_analysis_service.OfferNotInListError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offre introuvable dans votre liste.",
        ) from exc

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette offre n'a pas encore été analysée. Veuillez d'abord l'analyser.",
        )

    requirements = OfferRequirements.model_validate(analysis.data)
    return calculate_matching(profile, requirements)
