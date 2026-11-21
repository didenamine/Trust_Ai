"""US12 - Score de compatibilité & US13 - Explication du matching.

Compares a CandidateProfile (US05/US06/US07) against OfferRequirements (US09)
with fixed weights:
- Skills: 50%
- Experience: 30%
- Education: 20%
"""

from app.schemas.matching import (
    DimensionScore,
    EducationMatchDetail,
    ExperienceMatchDetail,
    MatchingBand,
    MatchingDetails,
    MatchingDimensionScores,
    MatchingResult,
    SkillMatch,
)
from app.schemas.offer_analysis import OfferRequirements
from app.schemas.profile import CandidateProfile
from app.schemas.shared import Skill, normalize_skill_name

SKILLS_WEIGHT = 50
EXPERIENCE_WEIGHT = 30
EDUCATION_WEIGHT = 20


def _clean_alphanumeric(text: str) -> str:
    return "".join(c for c in text if c.isalnum())


def _match_skill(req_key: str, candidate_keys: set[str]) -> bool:
    """Check if a required skill key matches any candidate skill key.

    Matches exact keys, alphanumeric variations ('fast-api' vs 'fastapi'),
    or common variant inclusions ('react' vs 'reactjs').
    """
    if req_key in candidate_keys:
        return True

    req_clean = _clean_alphanumeric(req_key)

    for cand_key in candidate_keys:
        cand_clean = _clean_alphanumeric(cand_key)

        if req_clean and req_clean == cand_clean:
            return True

        if (
            len(req_clean) >= 3
            and len(cand_clean) >= 3
            and (req_clean in cand_clean or cand_clean in req_clean)
        ):
            return True

    return False


def _compute_skills_matching(
    profile: CandidateProfile, requirements: OfferRequirements
) -> tuple[DimensionScore, list[SkillMatch], list[SkillMatch]]:
    candidate_keys = profile.skill_keys()

    # Collect required skills from offer
    req_skills_map: dict[str, Skill] = {}
    for s in requirements.skills:
        req_skills_map[s.key] = s
    for exp in requirements.experiences:
        for s_name in exp.skills:
            k = normalize_skill_name(s_name)
            if k not in req_skills_map:
                req_skills_map[k] = Skill(name=s_name)

    if not req_skills_map:
        # No specific skills required by the offer
        score = DimensionScore(
            weight=SKILLS_WEIGHT,
            points=float(SKILLS_WEIGHT),
            max_points=float(SKILLS_WEIGHT),
            ratio=1.0,
        )
        return score, [], []

    matched: list[SkillMatch] = []
    missing: list[SkillMatch] = []

    for key, skill in req_skills_map.items():
        is_matched = _match_skill(key, candidate_keys)
        match_obj = SkillMatch(name=skill.name, category=skill.category, matched=is_matched)
        if is_matched:
            matched.append(match_obj)
        else:
            missing.append(match_obj)

    ratio = len(matched) / len(req_skills_map)
    points = round(ratio * SKILLS_WEIGHT, 2)
    score = DimensionScore(
        weight=SKILLS_WEIGHT, points=points, max_points=float(SKILLS_WEIGHT), ratio=round(ratio, 2)
    )
    return score, matched, missing


def _compute_experience_matching(
    profile: CandidateProfile, requirements: OfferRequirements
) -> tuple[DimensionScore, ExperienceMatchDetail]:
    # Extract minimum years from requirements
    min_years_list = [
        exp.min_years for exp in requirements.experiences if exp.min_years is not None
    ]
    required_years = float(max(min_years_list)) if min_years_list else 0.0

    # Calculate candidate's actual experience in years (1 decimal)
    candidate_months = profile.total_experience_months()
    candidate_years = round(candidate_months / 12.0, 1)

    if required_years <= 0.0:
        ratio = 1.0
        points = float(EXPERIENCE_WEIGHT)
        meets = True
    else:
        meets = candidate_years >= required_years
        ratio = min(1.0, candidate_years / required_years)
        points = round(ratio * EXPERIENCE_WEIGHT, 2)

    score = DimensionScore(
        weight=EXPERIENCE_WEIGHT,
        points=points,
        max_points=float(EXPERIENCE_WEIGHT),
        ratio=round(ratio, 2),
    )
    detail = ExperienceMatchDetail(
        candidate_years=candidate_years,
        required_years=required_years,
        meets_requirement=meets,
    )
    return score, detail


def _compute_education_matching(
    profile: CandidateProfile, requirements: OfferRequirements
) -> tuple[DimensionScore, EducationMatchDetail]:
    # Find highest required level in offer
    req_levels = [edu.level for edu in requirements.education if edu.level is not None]
    required_level = max(req_levels, key=lambda lvl: lvl.rank) if req_levels else None

    # Candidate's highest level
    candidate_level = profile.highest_education_level()

    candidate_rank = candidate_level.rank if candidate_level is not None else None
    required_rank = required_level.rank if required_level is not None else None

    if required_level is None:
        ratio = 1.0
        points = float(EDUCATION_WEIGHT)
        meets = True
    else:
        if candidate_rank is not None and candidate_rank >= required_rank:
            ratio = 1.0
            points = float(EDUCATION_WEIGHT)
            meets = True
        elif candidate_rank is not None:
            # Candidate has a degree, but lower rank
            rank_diff = required_rank - candidate_rank
            ratio = max(0.0, 1.0 - (rank_diff * 0.35))
            points = round(ratio * EDUCATION_WEIGHT, 2)
            meets = False
        else:
            ratio = 0.0
            points = 0.0
            meets = False

    score = DimensionScore(
        weight=EDUCATION_WEIGHT,
        points=points,
        max_points=float(EDUCATION_WEIGHT),
        ratio=round(ratio, 2),
    )
    detail = EducationMatchDetail(
        candidate_level=candidate_level,
        required_level=required_level,
        candidate_rank=candidate_rank,
        required_rank=required_rank,
        meets_requirement=meets,
    )
    return score, detail


def _build_explanations(
    matched_skills: list[SkillMatch],
    missing_skills: list[SkillMatch],
    exp_detail: ExperienceMatchDetail,
    edu_detail: EducationMatchDetail,
) -> tuple[list[str], list[str]]:
    """Build textual explanations for US13 (strengths and areas to strengthen)."""
    strengths: list[str] = []
    improvements: list[str] = []

    # Skills
    if matched_skills:
        names = ", ".join(s.name for s in matched_skills[:5])
        strengths.append(f"{len(matched_skills)} compétence(s) requise(s) validée(s) : {names}.")
    if missing_skills:
        names = ", ".join(s.name for s in missing_skills[:5])
        improvements.append(
            f"{len(missing_skills)} compétence(s) demandée(s) manquante(s) : {names}."
        )

    # Experience
    if exp_detail.meets_requirement:
        if exp_detail.required_years > 0:
            strengths.append(
                f"Expérience suffisante ({exp_detail.candidate_years} an(s) pour {exp_detail.required_years} an(s) exigé(s))."
            )
        else:
            strengths.append(
                f"Expérience professionnelle validée ({exp_detail.candidate_years} an(s))."
            )
    else:
        improvements.append(
            f"Expérience inférieure à l'exigence ({exp_detail.candidate_years} an(s) vs {exp_detail.required_years} an(s) demandé(s))."
        )

    # Education
    if edu_detail.meets_requirement:
        if edu_detail.required_level:
            strengths.append(
                f"Niveau d'études requis validé ({edu_detail.candidate_level.value if edu_detail.candidate_level else 'conforme'})."
            )
    else:
        req_val = edu_detail.required_level.value if edu_detail.required_level else "non spécifié"
        cand_val = (
            edu_detail.candidate_level.value
            if edu_detail.candidate_level
            else "aucun diplôme renseigné"
        )
        improvements.append(
            f"Niveau de formation requis non atteint (exigé : {req_val}, profil : {cand_val})."
        )

    return strengths, improvements


def _band(total: int) -> MatchingBand:
    if total >= 80:
        return MatchingBand.EXCELLENT
    if total >= 65:
        return MatchingBand.GOOD
    if total >= 45:
        return MatchingBand.MODERATE
    return MatchingBand.LOW


def calculate_matching(
    profile: CandidateProfile, requirements: OfferRequirements
) -> MatchingResult:
    """Calculate the compatibility score between a candidate profile and an offer's requirements."""
    skills_score, matched_skills, missing_skills = _compute_skills_matching(profile, requirements)
    exp_score, exp_detail = _compute_experience_matching(profile, requirements)
    edu_score, edu_detail = _compute_education_matching(profile, requirements)

    total = int(round(skills_score.points + exp_score.points + edu_score.points))
    total = max(0, min(100, total))

    strengths, improvements = _build_explanations(
        matched_skills, missing_skills, exp_detail, edu_detail
    )

    return MatchingResult(
        total_score=total,
        band=_band(total),
        dimension_scores=MatchingDimensionScores(
            skills=skills_score,
            experience=exp_score,
            education=edu_score,
        ),
        details=MatchingDetails(
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            experience=exp_detail,
            education=edu_detail,
        ),
        strengths=strengths,
        improvements=improvements,
    )
