"""US09 - structured requirements extracted from a job offer.

The offer is analysed into the same building blocks as the candidate profile
(`schemas/shared.py`), but these are *requirements*, not facts about a person:
a required skill level, a minimum number of years and a minimum degree are not
the same thing as a candidate's skill level, experience and education.
Keeping separate models preserves that distinction while letting future
matching consume the same field names, enums and comparison keys.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.shared import (
    ContentLanguage,
    EducationLevel,
    EmploymentType,
    OptionalLongText,
    OptionalShortText,
    SchemaModel,
    ShortText,
    Skill,
)

OFFER_SCHEMA_VERSION = 1

_MAX_YEARS = 50
_SKILL_LEVEL_RANK = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}


def _clean_years(value: int | None) -> int | None:
    """Ignore years outside a plausible range instead of failing the whole analysis."""
    if value is None:
        return None
    return value if 0 <= value <= _MAX_YEARS else None


class ExperienceRequirement(SchemaModel):
    """What the employer asks for in terms of professional experience."""

    min_years: int | None = None
    max_years: int | None = None
    job_title: OptionalShortText | None = None
    employment_type: EmploymentType | None = None
    description: OptionalLongText | None = None
    skills: Annotated[list[ShortText], Field(max_length=50)] = Field(default_factory=list)

    @field_validator("min_years", "max_years", mode="after")
    @classmethod
    def clean_years(cls, value: int | None) -> int | None:
        return _clean_years(value)

    @model_validator(mode="after")
    def check_years(self) -> Self:
        """A narrower maximum than minimum is a contradiction: drop the maximum."""
        if (
            self.min_years is not None
            and self.max_years is not None
            and self.max_years < self.min_years
        ):
            self.max_years = None
        return self


class EducationRequirement(SchemaModel):
    """The minimum education / qualification the offer asks for."""

    level: EducationLevel | None = None
    degree: OptionalShortText | None = None
    field_of_study: OptionalShortText | None = None
    description: OptionalLongText | None = None


def _merge_required_skills(skills: list[Skill]) -> list[Skill]:
    """Same normalisation as the profile: one entry per skill key, best level wins."""
    merged: dict[str, Skill] = {}
    for skill in skills:
        key = skill.key
        current = merged.get(key)
        if current is None:
            merged[key] = skill.model_copy(deep=True)
        elif skill.level is not None and (
            current.level is None
            or _SKILL_LEVEL_RANK[skill.level] > _SKILL_LEVEL_RANK[current.level]
        ):
            current.level = skill.level
    return list(merged.values())


class OfferRequirements(SchemaModel):
    """The four US09 requirements, comparable with `CandidateProfile`."""

    schema_version: Literal[1] = OFFER_SCHEMA_VERSION
    language: ContentLanguage
    job_title: OptionalShortText | None = None
    skills: Annotated[list[Skill], Field(max_length=150)] = Field(default_factory=list)
    experiences: Annotated[list[ExperienceRequirement], Field(max_length=50)] = Field(
        default_factory=list
    )
    education: Annotated[list[EducationRequirement], Field(max_length=30)] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def clean_lists(self) -> Self:
        self.skills = _merge_required_skills(self.skills)
        return self


class OfferAnalysisOut(BaseModel):
    """A stored US09 analysis returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    requirements: OfferRequirements
    created_at: datetime
    updated_at: datetime
