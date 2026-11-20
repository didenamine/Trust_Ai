"""Building blocks shared by the candidate profile (T-09) and the analysed job offer (US09).

The CV and the offer are turned into JSON of the same shape so that matching (US12),
its explanation (US13) and missing skills (US33) can compare them field by field.
Reuse these types in the offer schema instead of redefining them.

Enum values are stable English identifiers stored in the database; the frontend
translates them for display.
"""

import re
import unicodedata
from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints


class SchemaModel(BaseModel):
    """Base for every profile / offer model.

    Unknown keys are ignored rather than rejected: the LLM (US05, US09) sometimes adds
    fields of its own, and that must not make a whole analysis fail.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


# --- Text types ---------------------------------------------------------------


def blank_to_none(value: Any) -> Any:
    """Forms and the LLM both send "" for "unknown": store it as null."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
MediumText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]

OptionalShortText = Annotated[ShortText | None, BeforeValidator(blank_to_none)]
OptionalLongText = Annotated[LongText | None, BeforeValidator(blank_to_none)]


# --- Partial dates ------------------------------------------------------------

_MONTH_YEAR_RE = re.compile(r"^(\d{1,2})[/.-](\d{4})$")  # 03/2021, 3-2021, 03.2021
_YEAR_MONTH_RE = re.compile(r"^(\d{4})[/.-](\d{1,2})(?:[/.-]\d{1,2})?$")  # 2021-3, 2021-03-15


def _normalize_partial_date(value: Any) -> Any:
    """Bring the usual CV date formats to "YYYY" or "YYYY-MM"."""
    value = blank_to_none(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, date):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, str):
        value = value.strip()
        if match := _MONTH_YEAR_RE.match(value):
            month, year = match.groups()
            return f"{year}-{int(month):02d}"
        if match := _YEAR_MONTH_RE.match(value):
            year, month = match.groups()
            return f"{year}-{int(month):02d}"
    return value


PartialDate = Annotated[
    str,
    BeforeValidator(_normalize_partial_date),
    StringConstraints(pattern=r"^(19|20)\d{2}(-(0[1-9]|1[0-2]))?$"),
]
"""A date as precise as a CV gives it: "2021" or "2021-03"."""

OptionalPartialDate = Annotated[PartialDate | None, BeforeValidator(blank_to_none)]


def partial_date_bounds(value: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """First and last (year, month) a partial date can mean: "2021" -> (2021, 1), (2021, 12)."""
    year, _, month = value.partition("-")
    if month:
        return (int(year), int(month)), (int(year), int(month))
    return (int(year), 1), (int(year), 12)


# --- Enums --------------------------------------------------------------------


class ContentLanguage(StrEnum):
    """Language the CV or the offer is written in (US05, US09)."""

    FR = "fr"
    EN = "en"


class SkillCategory(StrEnum):
    HARD = "hard"  # technical skills, tools, methods: Python, React, Scrum, SQL...
    SOFT = "soft"  # communication, leadership, teamwork...


class SkillLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LanguageLevel(StrEnum):
    """CEFR levels, plus native speaker."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    NATIVE = "native"

    @property
    def rank(self) -> int:
        return list(LanguageLevel).index(self)


class EducationLevel(StrEnum):
    """Highest degree, comparable between a profile and an offer ("Bac+5 exigé").

    French / Tunisian equivalents: secondary = Bac, associate = Bac+2 (BTS, DUT),
    bachelor = Bac+3 (Licence), master = Bac+5 (Master, diplôme d'ingénieur),
    doctorate = Bac+8 (Doctorat).
    """

    SECONDARY = "secondary"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"

    @property
    def rank(self) -> int:
        return list(EducationLevel).index(self)


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERNSHIP = "internship"  # stage
    APPRENTICESHIP = "apprenticeship"  # alternance
    FREELANCE = "freelance"
    VOLUNTEER = "volunteer"


# --- Skills -------------------------------------------------------------------


def normalize_skill_name(name: str) -> str:
    """Comparison key for a skill: lowercase, no accents, single spaces.

    Keeps the characters that make a skill different ("C" vs "C++" vs "C#", ".NET").
    Fuzzy matching of variants ("ReactJS" vs "React") is US12's job, on top of this key.
    """
    without_accents = "".join(
        char for char in unicodedata.normalize("NFKD", name) if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().split())


class Skill(SchemaModel):
    name: ShortText
    category: SkillCategory = SkillCategory.HARD
    level: SkillLevel | None = None

    @property
    def key(self) -> str:
        return normalize_skill_name(self.name)


LanguageCode = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().lower() if isinstance(v, str) else v),
    StringConstraints(pattern=r"^[a-z]{2}$"),
]
"""ISO 639-1 code: "en", "fr", "ar"..."""


class LanguageSkill(SchemaModel):
    name: ShortText  # as written in the CV: "Anglais", "English"...
    # The ISO code makes "Anglais" and "English" compare as equal.
    code: Annotated[LanguageCode | None, BeforeValidator(blank_to_none)] = None
    level: LanguageLevel | None = None

    @property
    def key(self) -> str:
        return self.code or normalize_skill_name(self.name)
