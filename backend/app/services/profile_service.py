"""Read and write candidate profiles (T-09).

The single entry point for every feature that touches the profile:
US05 saves the analysed CV with `save_profile(..., source=ProfileSource.CV_ANALYSIS)`,
US06 / US07 save the candidate's input with `ProfileSource.MANUAL`, and matching (US12),
US14, US31... read it with `get_candidate_profile`.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.schemas.profile import CandidateProfile


class ProfileSource(StrEnum):
    CV_ANALYSIS = "cv_analysis"  # US05
    MANUAL = "manual"  # US06


def get_profile_record(db: Session, user_id: uuid.UUID) -> Profile | None:
    return db.query(Profile).filter(Profile.user_id == user_id).first()


def get_candidate_profile(db: Session, user_id: uuid.UUID) -> CandidateProfile | None:
    """The candidate's profile, validated, or None if they don't have one yet."""
    record = get_profile_record(db, user_id)
    return to_candidate_profile(record) if record else None


def to_candidate_profile(record: Profile) -> CandidateProfile:
    return CandidateProfile.model_validate(record.data)


def save_profile(
    db: Session,
    *,
    user_id: uuid.UUID,
    profile: CandidateProfile,
    source: ProfileSource,
    cv_document_id: uuid.UUID | None = None,
) -> Profile:
    """Create or replace the candidate's profile.

    `source` records how the profile was first created and is kept on later edits;
    a new CV analysis (US05) resets it to "cv_analysis" and links the analysed CV.
    """
    record = get_profile_record(db, user_id)
    if record is None:
        record = Profile(user_id=user_id, source=source.value)
        db.add(record)
    elif source is ProfileSource.CV_ANALYSIS:
        record.source = source.value

    record.data = profile.model_dump(mode="json")
    if cv_document_id is not None:
        record.cv_document_id = cv_document_id
    record.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(record)
    return record
