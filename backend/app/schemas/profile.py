"""The common candidate profile (T-09).

One model, filled three ways and read by most of the app:

- written by US05 (analysis of the imported CV by the LLM) and US06 (manual entry),
- shown and corrected by US07,
- compared with the analysed offer by US12 / US13 / US33 (matching, explanation,
  missing skills), used by US14 (CV adapted to an offer) and checked by US16 (Truth Guard),
- summarised by US31 (dashboard).

Deliberately left out: photo, age / date of birth, gender, nationality, marital status.
They must play no part in matching, so the profile never stores them.

See docs/PROFIL.md for the field-by-field description.
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, HttpUrl, model_validator

from app.schemas.shared import (
    ContentLanguage,
    EducationLevel,
    EmploymentType,
    LanguageSkill,
    MediumText,
    OptionalLongText,
    OptionalPartialDate,
    OptionalShortText,
    SchemaModel,
    ShortText,
    Skill,
    SkillLevel,
    blank_to_none,
    normalize_skill_name,
    partial_date_bounds,
)

PROFILE_SCHEMA_VERSION = 1


def _add_url_scheme(value: Any) -> Any:
    """CVs write "linkedin.com/in/x" or "github.com/x": make them real URLs."""
    value = blank_to_none(value)
    if isinstance(value, str) and "://" not in value:
        return f"https://{value.strip()}"
    return value


Url = Annotated[HttpUrl, BeforeValidator(_add_url_scheme)]
OptionalUrl = Annotated[Url | None, BeforeValidator(blank_to_none)]


def _new_id() -> str:
    return uuid.uuid4().hex


class ProfileItem(SchemaModel):
    """An entry in one of the profile's lists.

    The id is stable across edits, so the frontend (US07) can track rows and other
    features can point to a precise entry (US13 explanation, US16 Truth Guard).
    New entries get one automatically.
    """

    id: Annotated[str, Field(min_length=1, max_length=64)] = Field(default_factory=_new_id)


class DatedItem(ProfileItem):
    start_date: OptionalPartialDate = None
    end_date: OptionalPartialDate = None
    is_current: bool = False

    @model_validator(mode="after")
    def check_period(self) -> Self:
        if self.is_current:
            self.end_date = None
        if self.start_date and self.end_date:
            earliest_start, _ = partial_date_bounds(self.start_date)
            _, latest_end = partial_date_bounds(self.end_date)
            if latest_end < earliest_start:
                raise ValueError("La date de fin est antérieure à la date de début")
        return self

    def period_months(self, today: date | None = None) -> tuple[int, int] | None:
        """The period as month indexes (year * 12 + month - 1), end excluded.

        None when it can't be measured: no start date, or an end that is neither
        given nor "current".
        """
        if not self.start_date:
            return None
        (start_year, start_month), _ = partial_date_bounds(self.start_date)
        if self.is_current:
            today = today or date.today()
            end_year, end_month = today.year, today.month
        elif self.end_date:
            _, (end_year, end_month) = partial_date_bounds(self.end_date)
        else:
            return None
        start = start_year * 12 + start_month - 1
        end = end_year * 12 + end_month  # the end month counts as worked
        return (start, end) if end > start else None


class PersonalInfo(SchemaModel):
    full_name: OptionalShortText = None
    headline: OptionalShortText = None
    """The job title the candidate presents themselves with, e.g. "Développeur full-stack"."""
    email: Annotated[EmailStr | None, BeforeValidator(blank_to_none)] = None
    phone: Annotated[
        Annotated[str, Field(min_length=1, max_length=50)] | None, BeforeValidator(blank_to_none)
    ] = None
    location: OptionalShortText = None
    links: Annotated[list[Url], Field(max_length=10)] = []
    """LinkedIn, GitHub, portfolio..."""


class Experience(DatedItem):
    job_title: ShortText
    company: OptionalShortText = None
    location: OptionalShortText = None
    employment_type: EmploymentType | None = None
    description: OptionalLongText = None
    achievements: Annotated[list[MediumText], Field(max_length=20)] = []
    skills: Annotated[list[ShortText], Field(max_length=50)] = []
    """Skills used in this job, as names (they also appear in `CandidateProfile.skills`)."""


class Education(DatedItem):
    degree: ShortText
    """As written in the CV: "Licence en informatique", "Diplôme d'ingénieur"..."""
    level: EducationLevel | None = None
    field_of_study: OptionalShortText = None
    institution: OptionalShortText = None
    location: OptionalShortText = None
    description: OptionalLongText = None


class Certification(ProfileItem):
    name: ShortText
    issuer: OptionalShortText = None
    issue_date: OptionalPartialDate = None
    url: OptionalUrl = None


class Project(DatedItem):
    name: ShortText
    description: OptionalLongText = None
    skills: Annotated[list[ShortText], Field(max_length=50)] = []
    url: OptionalUrl = None


_SKILL_LEVEL_RANK = {level: rank for rank, level in enumerate(SkillLevel)}


class CandidateProfile(SchemaModel):
    """The structured profile of a candidate, stored as JSON (JSONB in PostgreSQL)."""

    schema_version: Literal[1] = PROFILE_SCHEMA_VERSION
    language: ContentLanguage
    """Language the profile's content is written in (detected from the CV by US05)."""

    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: OptionalLongText = None
    skills: Annotated[list[Skill], Field(max_length=150)] = []
    experiences: Annotated[list[Experience], Field(max_length=50)] = []
    education: Annotated[list[Education], Field(max_length=30)] = []
    languages: Annotated[list[LanguageSkill], Field(max_length=20)] = []
    certifications: Annotated[list[Certification], Field(max_length=50)] = []
    projects: Annotated[list[Project], Field(max_length=50)] = []

    @model_validator(mode="after")
    def clean_lists(self) -> Self:
        self.skills = _merge_skills(self.skills)
        self.languages = _merge_languages(self.languages)
        _ensure_unique_ids(
            [*self.experiences, *self.education, *self.certifications, *self.projects]
        )
        return self

    # --- Helpers for matching (US12), dashboard (US31)... ---------------------

    def skill_keys(self) -> set[str]:
        """Every skill the candidate shows, normalised: the skills list plus the skills
        used in experiences and projects."""
        keys = {skill.key for skill in self.skills}
        for item in [*self.experiences, *self.projects]:
            keys.update(normalize_skill_name(name) for name in item.skills)
        return keys

    def total_experience_months(
        self, today: date | None = None, *, include_internships: bool = True
    ) -> int:
        """Months of professional experience. Overlapping jobs are only counted once;
        volunteering is not counted."""
        excluded = {EmploymentType.VOLUNTEER}
        if not include_internships:
            excluded |= {EmploymentType.INTERNSHIP, EmploymentType.APPRENTICESHIP}

        periods = sorted(
            period
            for experience in self.experiences
            if experience.employment_type not in excluded
            and (period := experience.period_months(today)) is not None
        )
        total, current_start, current_end = 0, None, None
        for start, end in periods:
            if current_end is None or start > current_end:
                if current_end is not None:
                    total += current_end - current_start
                current_start, current_end = start, end
            else:
                current_end = max(current_end, end)
        if current_end is not None:
            total += current_end - current_start
        return total

    def highest_education_level(self) -> EducationLevel | None:
        levels = [item.level for item in self.education if item.level is not None]
        return max(levels, key=lambda level: level.rank) if levels else None


def _merge_skills(skills: list[Skill]) -> list[Skill]:
    """Remove duplicates ("Python", "python "), keeping the first one and the best level."""
    merged: dict[str, Skill] = {}
    for skill in skills:
        existing = merged.get(skill.key)
        if existing is None:
            merged[skill.key] = skill
        elif skill.level and (
            existing.level is None
            or _SKILL_LEVEL_RANK[skill.level] > _SKILL_LEVEL_RANK[existing.level]
        ):
            existing.level = skill.level
    return list(merged.values())


def _merge_languages(languages: list[LanguageSkill]) -> list[LanguageSkill]:
    merged: dict[str, LanguageSkill] = {}
    for language in languages:
        existing = merged.get(language.key)
        if existing is None:
            merged[language.key] = language
        elif language.level and (
            existing.level is None or language.level.rank > existing.level.rank
        ):
            existing.level = language.level
    return list(merged.values())


def _ensure_unique_ids(items: list[ProfileItem]) -> None:
    """Give a new id to any entry whose id is already used (e.g. a row copied in the UI)."""
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            item.id = _new_id()
        seen.add(item.id)


class ProfileOut(BaseModel):
    """What GET / PUT /api/profile/me return: the profile and where it comes from."""

    profile: CandidateProfile
    source: str
    cv_document_id: uuid.UUID | None = None
    updated_at: datetime
