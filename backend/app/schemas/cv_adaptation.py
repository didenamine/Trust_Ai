"""US14 - CV adapté à une offre.

Le LLM ne réécrit pas le CV librement : il reformule les textes du profil existant
(titre, résumé, expériences) pour les rapprocher de l'offre, et ordonne les compétences
déjà présentes. Les compétences demandées mais absentes du profil ne sont jamais ajoutées
au CV : elles restent un écart signalé au candidat (calculé par le matching, US12).

Le CV complet (coordonnées, dates, formations, langues...) est ensuite assemblé à partir du
profil par `services/ats_cv_builder.py`: voir `schemas/ats_cv.py`.

Dans le MVP, ce contenu n'est pas vérifié (Truth Guard arrive en Release 2).
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.ats_cv import ATSCVDocument
from app.schemas.shared import (
    ContentLanguage,
    MediumText,
    OptionalLongText,
    OptionalShortText,
    SchemaModel,
    ShortText,
    normalize_skill_name,
)

ADAPTATION_SCHEMA_VERSION = 1


class AdaptedExperience(SchemaModel):
    """Texte reformulé d'une expérience du profil, rattaché par son identifiant."""

    experience_id: Annotated[str, Field(min_length=1, max_length=64)]
    description: OptionalLongText = None
    achievements: Annotated[list[MediumText], Field(max_length=20)] = Field(default_factory=list)


class AdaptedCV(SchemaModel):
    """Les parties du CV que l'adaptation modifie (réponse structurée du LLM)."""

    schema_version: Literal[1] = ADAPTATION_SCHEMA_VERSION
    language: ContentLanguage
    headline: OptionalShortText = None
    summary: OptionalLongText = None
    # Compétences du profil, de la plus pertinente pour l'offre à la moins pertinente.
    highlighted_skills: Annotated[list[ShortText], Field(max_length=150)] = Field(
        default_factory=list
    )
    experiences: Annotated[list[AdaptedExperience], Field(max_length=50)] = Field(
        default_factory=list
    )
    # Ce qui a été modifié et pourquoi, pour que le candidat puisse relire.
    changes: Annotated[list[MediumText], Field(max_length=30)] = Field(default_factory=list)

    @model_validator(mode="after")
    def clean_lists(self) -> Self:
        """Une seule entrée par compétence (casse et accents ignorés) et par expérience."""
        seen_skills: set[str] = set()
        skills: list[str] = []
        for name in self.highlighted_skills:
            key = normalize_skill_name(name)
            if key not in seen_skills:
                seen_skills.add(key)
                skills.append(name)
        self.highlighted_skills = skills

        seen_ids: set[str] = set()
        experiences: list[AdaptedExperience] = []
        for experience in self.experiences:
            if experience.experience_id not in seen_ids:
                seen_ids.add(experience.experience_id)
                experiences.append(experience)
        self.experiences = experiences
        return self


class CVAdaptationOut(BaseModel):
    """Le CV adapté à une offre, tel que renvoyé par l'API."""

    id: uuid.UUID
    offer_id: uuid.UUID
    matching_score: int
    # Compétences demandées par l'offre mais absentes du profil : jamais ajoutées au CV.
    missing_skills: list[str]
    # Les textes adaptés par le LLM, avec ce qui a changé.
    adapted_cv: AdaptedCV
    # Le CV complet au format ATS, et le même en texte brut (à copier ou télécharger).
    document: ATSCVDocument
    ats_text: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: Any, *, document: ATSCVDocument, ats_text: str) -> Self:
        return cls(
            id=record.id,
            offer_id=record.offer_id,
            matching_score=record.matching_score,
            missing_skills=list(record.missing_skills),
            adapted_cv=AdaptedCV.model_validate(record.data),
            document=document,
            ats_text=ats_text,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
