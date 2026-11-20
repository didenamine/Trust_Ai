from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import CandidateProfile, ProfileOut
from app.services import profile_service
from app.services.profile_service import ProfileSource

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=ProfileOut)
def get_my_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileOut:
    record = profile_service.get_profile_record(db, current_user.id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun profil")
    return ProfileOut.from_record(record)


@router.put("/me", response_model=ProfileOut)
def save_my_profile(
    profile: CandidateProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    """Create or replace the profile with the candidate's input (US06 entry, US07 edits)."""
    record = profile_service.save_profile(
        db, user_id=current_user.id, profile=profile, source=ProfileSource.MANUAL
    )
    return ProfileOut.from_record(record)
