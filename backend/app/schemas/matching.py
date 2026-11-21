"""US12 & US13 - Candidate Profile vs Job Offer Matching schema.

Fixed weights defined for Sprint 1 (US12 acceptance criteria):
- Skills: 50%
- Experience: 30%
- Education: 20%

Reused by:
- US13: Strengths and missing skills explanation
- US31: Dashboard matching block
- US33: Prioritised skill gaps
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.shared import EducationLevel, SchemaModel, ShortText, SkillCategory


class MatchingBand(StrEnum):
    EXCELLENT = "excellent"  # >= 80%
    GOOD = "good"  # >= 65%
    MODERATE = "moderate"  # >= 45%
    LOW = "low"  # < 45%


class DimensionScore(SchemaModel):
    """Score breakdown for one matching dimension (skills, experience, education)."""

    weight: int = Field(ge=0, le=100, description="Pondération fixe de la dimension (ex: 50)")
    points: float = Field(ge=0, description="Points obtenus pour cette dimension")
    max_points: float = Field(ge=0, description="Points maximum possibles")
    ratio: float = Field(ge=0, le=1, description="Ratio de complétion entre 0 et 1")


class SkillMatch(SchemaModel):
    name: ShortText
    category: SkillCategory = SkillCategory.HARD
    matched: bool = True


class ExperienceMatchDetail(SchemaModel):
    candidate_years: float = Field(ge=0, description="Années d'expérience du candidat")
    required_years: float = Field(ge=0, description="Années d'expérience minimales demandées par l'offre")
    meets_requirement: bool


class EducationMatchDetail(SchemaModel):
    candidate_level: EducationLevel | None = None
    required_level: EducationLevel | None = None
    candidate_rank: int | None = None
    required_rank: int | None = None
    meets_requirement: bool


class MatchingDetails(SchemaModel):
    """Detailed comparison results across the three dimensions."""

    matched_skills: list[SkillMatch] = Field(default_factory=list)
    missing_skills: list[SkillMatch] = Field(default_factory=list)
    experience: ExperienceMatchDetail
    education: EducationMatchDetail


class MatchingDimensionScores(SchemaModel):
    skills: DimensionScore
    experience: DimensionScore
    education: DimensionScore


class MatchingResult(SchemaModel):
    """The complete result of comparing a CandidateProfile to OfferRequirements.

    Designed for US12 (Score) and US13 (Explanation) and consumed by US31 / US33.
    """

    total_score: int = Field(ge=0, le=100, description="Score global de compatibilité sur 100")
    band: MatchingBand
    dimension_scores: MatchingDimensionScores
    details: MatchingDetails
    strengths: list[str] = Field(
        default_factory=list, description="Points forts expliqués (US13)"
    )
    improvements: list[str] = Field(
        default_factory=list, description="Axes d'amélioration / compétences manquantes expliquées (US13)"
    )
