"""US24 - ATS analysis of an imported CV.

The JSON stored in `ats_analyses.result` is described by `ATSAnalysisResult`.
It deliberately contains **no CV text**: findings use stable codes, section ids,
line/page references and structured checks only.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator

from app.schemas.shared import ContentLanguage, SchemaModel

SCORING_VERSION = 1

# Static, translatable limitation codes (no CV-derived text is stored).
LIMITATIONS = (
    "ats.estimate_only",
    "ats.no_target_job",
    "ats.no_ocr",
)


class ATSSectionId(StrEnum):
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"


class ATSStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    MISSING = "missing"
    NA = "na"


class ATSSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ATSKeywordKind(StrEnum):
    HARD_SKILL = "hard_skill"
    TOOL = "tool"
    METHOD = "method"
    ACTION_VERB = "action_verb"
    GENERIC = "generic"


class ATSBand(StrEnum):
    LOW = "low"
    TO_IMPROVE = "to_improve"
    GOOD = "good"
    EXCELLENT = "excellent"


class ATSReadingLocation(StrEnum):
    BODY = "body"
    HEADER = "header"
    FOOTER = "footer"
    TABLE = "table"
    TEXTBOX = "textbox"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ATSSectionFinding(SchemaModel):
    """A canonical CV section, with stable check codes instead of CV snippets."""

    section: ATSSectionId
    status: ATSStatus
    present: bool
    detection: str
    line: int | None = None
    order_index: int | None = None
    checks: dict[str, bool] = {}
    issues: list[str] = []


class ATSKeywordFinding(SchemaModel):
    """A normalised keyword found (or claimed) in the CV text."""

    canonical: str
    kind: ATSKeywordKind
    verified: bool
    line: int | None = None
    section: ATSSectionId | None = None
    occurrences: int = 0
    alias_count: int = 0
    in_skills_section: bool = False
    in_context_section: bool = False

    @field_validator("canonical")
    @classmethod
    def _clean_canonical(cls, value: str) -> str:
        # Keep structured terms ("C++", ".NET", "project management"), never sentences
        # that could accidentally persist personal information from the CV.
        value = " ".join(value.split())
        if not 2 <= len(value) <= 60 or "\n" in value:
            raise ValueError("Invalid keyword")
        return value


class ATSKeywordSummary(SchemaModel):
    specific_count: int = 0
    action_verb_count: int = 0
    generic_count: int = 0
    verified_count: int = 0
    repeated_count: int = 0
    max_occurrences: int = 0
    specificity_ratio: float = 0.0
    terminology_issues: int = 0


class ATSReadabilityFinding(SchemaModel):
    """A parsing observation. Only findings with evidence of degraded extraction
    carry a deduction; layout alone is reported as a warning."""

    code: str
    severity: ATSSeverity
    location: ATSReadingLocation = ATSReadingLocation.UNKNOWN
    page: int | None = None
    line: int | None = None
    degraded_extraction: bool = False
    deduction: float = 0.0

    @field_validator("deduction")
    @classmethod
    def _non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Deduction cannot be negative")
        return value


class ATSCriterion(SchemaModel):
    key: str
    label_key: str
    weight: int
    points: float
    status: ATSStatus
    applicable: bool = True
    reason_code: str | None = None

    @property
    def ratio(self) -> float:
        if not self.applicable or self.weight <= 0:
            return 0.0
        return min(max(self.points / self.weight, 0.0), 1.0)


class ATSScoreBreakdown(SchemaModel):
    total: int
    band: ATSBand
    scoring_version: int
    denominator: int
    dimensions: list[ATSCriterion]
    criteria: list[ATSCriterion]
    na_sections: list[ATSSectionId] = []


class ATSAnalysisResult(SchemaModel):
    language: ContentLanguage
    sections: list[ATSSectionFinding]
    keywords: ATSKeywordSummary
    keyword_findings: list[ATSKeywordFinding]
    readability: list[ATSReadabilityFinding]
    score: ATSScoreBreakdown
    limitations: list[str] = list(LIMITATIONS)


class ATSAnalysisOut(BaseModel):
    """What the ATS endpoints return: metadata plus the stored analysis result."""

    id: uuid.UUID
    cv_document_id: uuid.UUID
    cv_uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    scoring_version: int
    score: ATSScoreBreakdown
    result: ATSAnalysisResult

    @classmethod
    def from_record(cls, record: Any) -> "ATSAnalysisOut":
        result = ATSAnalysisResult.model_validate(record.result)
        return cls(
            id=record.id,
            cv_document_id=record.cv_document_id,
            cv_uploaded_at=record.cv_uploaded_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
            scoring_version=record.scoring_version,
            score=result.score,
            result=result,
        )


# --- LLM answer ----------------------------------------------------------------


# Only structured references are requested: no snippet / quote / raw heading text.
class ATSLLMSection(SchemaModel):
    section: ATSSectionId
    line: int | None = None
    confidence: float = 0.0


class ATSLLMKeyword(SchemaModel):
    canonical: str
    kind: ATSKeywordKind
    line: int | None = None
    section: ATSSectionId | None = None
    alias_count: int = 0


class ATSLLMAnswer(SchemaModel):
    sections: list[ATSLLMSection] = []
    keywords: list[ATSLLMKeyword] = []
