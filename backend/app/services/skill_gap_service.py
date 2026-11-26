"""US33 - Compétences manquantes et prioritaires.

Reuses US12's `calculate_matching` (a pure comparison, no LLM call) across every
offer the candidate has already analysed (US09), and ranks the skills that come
up missing the most often. Nothing is persisted: like the matching endpoint
itself, the result is recomputed fresh each time from the profile and the
stored offer analyses, so it is never stale.
"""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_offer import UserOffer
from app.models.offer_analysis import OfferAnalysis
from app.schemas.offer_analysis import OfferRequirements
from app.schemas.profile import CandidateProfile
from app.schemas.shared import SkillCategory
from app.schemas.skill_gap import PrioritizedSkill, SkillGapResult
from app.services.matching_service import calculate_matching


def compute_skill_gaps(
    db: Session, *, user_id: uuid.UUID, profile: CandidateProfile
) -> SkillGapResult:
    counts: dict[str, int] = defaultdict(int)
    display_names: dict[str, str] = {}
    categories: dict[str, SkillCategory] = {}
    offers_considered = 0

    links = db.scalars(select(UserOffer).where(UserOffer.user_id == user_id)).all()
    for link in links:
        analysis = db.scalars(
            select(OfferAnalysis).where(OfferAnalysis.offer_id == link.offer_id)
        ).first()
        if analysis is None:
            continue  # not analysed yet (US09): nothing to compare against

        offers_considered += 1
        requirements = OfferRequirements.model_validate(analysis.data)
        matching = calculate_matching(profile, requirements)

        for skill in matching.details.missing_skills:
            key = skill.name.strip().lower()
            counts[key] += 1
            display_names.setdefault(key, skill.name)
            categories.setdefault(key, skill.category)

    skills = [
        PrioritizedSkill(
            name=display_names[key],
            category=categories[key],
            missing_in_offers=count,
        )
        for key, count in counts.items()
    ]
    # Most frequently missing first; hard skills before soft on a tie; then alphabetical.
    skills.sort(
        key=lambda s: (-s.missing_in_offers, s.category != SkillCategory.HARD, s.name.lower())
    )

    return SkillGapResult(skills=skills, offers_considered=offers_considered)
