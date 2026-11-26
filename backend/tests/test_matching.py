"""US12 & US13 - Unit tests for candidate profile and job offer matching."""

import json
from pathlib import Path

from app.schemas.matching import MatchingBand
from app.schemas.offer_analysis import (
    EducationRequirement,
    ExperienceRequirement,
    OfferRequirements,
)
from app.schemas.profile import CandidateProfile
from app.schemas.shared import (
    ContentLanguage,
    EducationLevel,
    Skill,
    SkillCategory,
)
from app.services.matching_service import (
    EDUCATION_WEIGHT,
    EXPERIENCE_WEIGHT,
    SKILLS_WEIGHT,
    calculate_matching,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_candidate_profile() -> CandidateProfile:
    with open(FIXTURES_DIR / "profile_fr.json", encoding="utf-8") as f:
        data = json.load(f)
    return CandidateProfile.model_validate(data)


def test_perfect_matching():
    """Candidate satisfies all required skills, experience and education."""
    profile = load_candidate_profile()

    offer = OfferRequirements(
        language=ContentLanguage.FR,
        job_title="Développeur Full-Stack Python",
        skills=[
            Skill(name="Python", category=SkillCategory.HARD),
            Skill(name="FastAPI", category=SkillCategory.HARD),
            Skill(name="React", category=SkillCategory.HARD),
        ],
        experiences=[ExperienceRequirement(min_years=1, job_title="Développeur Python")],
        education=[EducationRequirement(level=EducationLevel.BACHELOR)],
    )

    result = calculate_matching(profile, offer)

    assert result.total_score == 100
    assert result.band == MatchingBand.EXCELLENT
    assert result.dimension_scores.skills.points == SKILLS_WEIGHT
    assert result.dimension_scores.experience.points == EXPERIENCE_WEIGHT
    assert result.dimension_scores.education.points == EDUCATION_WEIGHT
    assert len(result.details.matched_skills) == 3
    assert len(result.details.missing_skills) == 0
    assert len(result.strengths) > 0
    assert len(result.improvements) == 0


def test_partial_matching_and_missing_skills():
    """Candidate misses some skills and has less experience than required."""
    profile = load_candidate_profile()

    offer = OfferRequirements(
        language=ContentLanguage.FR,
        job_title="Lead Architecte Java / Kubernetes",
        skills=[
            Skill(name="Python", category=SkillCategory.HARD),  # candidate has this
            Skill(name="Java", category=SkillCategory.HARD),  # missing
            Skill(name="Kubernetes", category=SkillCategory.HARD),  # missing
            Skill(name="AWS", category=SkillCategory.HARD),  # missing
        ],
        experiences=[ExperienceRequirement(min_years=5)],  # profile has less than 5 years
        education=[
            EducationRequirement(level=EducationLevel.MASTER)  # candidate has master (engineering)
        ],
    )

    result = calculate_matching(profile, offer)

    # 1 out of 4 skills = 25% of 50 = 12.5 points
    assert result.dimension_scores.skills.points == 12.5
    assert len(result.details.matched_skills) == 1
    assert len(result.details.missing_skills) == 3

    # Education does not meet Master (candidate has Bachelor)
    assert result.dimension_scores.education.points < EDUCATION_WEIGHT
    assert result.details.education.meets_requirement is False

    # Experience does not meet 5 years
    assert result.details.experience.meets_requirement is False
    assert result.dimension_scores.experience.points < EXPERIENCE_WEIGHT

    # Explanation US13
    assert any("manquante" in imp for imp in result.improvements)
    assert any("Expérience inférieure" in imp for imp in result.improvements)


def test_empty_requirements_gives_full_score():
    """An offer without constraints defaults to full compatibility."""
    profile = load_candidate_profile()

    offer = OfferRequirements(
        language=ContentLanguage.FR,
        job_title="Stage de découverte",
        skills=[],
        experiences=[],
        education=[],
    )

    result = calculate_matching(profile, offer)

    assert result.total_score == 100
    assert result.band == MatchingBand.EXCELLENT
    assert result.dimension_scores.skills.points == SKILLS_WEIGHT
    assert result.dimension_scores.experience.points == EXPERIENCE_WEIGHT
    assert result.dimension_scores.education.points == EDUCATION_WEIGHT


def test_fuzzy_skill_matching():
    """Skills like 'reactjs' or 'react.js' should match 'React'."""
    profile = load_candidate_profile()

    offer = OfferRequirements(
        language=ContentLanguage.FR,
        skills=[
            Skill(name="reactjs", category=SkillCategory.HARD),
            Skill(name="fast-api", category=SkillCategory.HARD),
        ],
        experiences=[],
        education=[],
    )

    result = calculate_matching(profile, offer)

    assert len(result.details.matched_skills) == 2
    assert len(result.details.missing_skills) == 0
    assert result.dimension_scores.skills.points == SKILLS_WEIGHT
