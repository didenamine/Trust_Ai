"""US14 - Tests du schéma du CV adapté."""

import pytest
from pydantic import ValidationError

from app.schemas.cv_adaptation import AdaptedCV
from app.schemas.shared import ContentLanguage
from app.services.llm import to_strict_json_schema

APP_SET_FIELDS = frozenset({"schema_version", "language"})


def test_minimal_adapted_cv_has_empty_defaults():
    cv = AdaptedCV(language=ContentLanguage.FR)

    assert cv.schema_version == 1
    assert cv.headline is None
    assert cv.summary is None
    assert cv.highlighted_skills == []
    assert cv.experiences == []
    assert cv.changes == []


def test_blank_texts_become_none():
    cv = AdaptedCV(language=ContentLanguage.FR, headline="   ", summary="")

    assert cv.headline is None
    assert cv.summary is None


def test_duplicate_skills_are_removed_ignoring_case_and_accents():
    cv = AdaptedCV(
        language=ContentLanguage.FR,
        highlighted_skills=["Python", "python", " PYTHON ", "FastAPI", "Gestion de projet"],
    )

    assert cv.highlighted_skills == ["Python", "FastAPI", "Gestion de projet"]


def test_duplicate_experience_ids_keep_the_first_entry():
    cv = AdaptedCV.model_validate(
        {
            "language": "en",
            "experiences": [
                {"experience_id": "exp-1", "description": "First version"},
                {"experience_id": "exp-1", "description": "Second version"},
                {"experience_id": "exp-2", "achievements": ["Cut costs by 20%"]},
            ],
        }
    )

    assert [e.experience_id for e in cv.experiences] == ["exp-1", "exp-2"]
    assert cv.experiences[0].description == "First version"


def test_experience_without_id_is_rejected():
    with pytest.raises(ValidationError):
        AdaptedCV.model_validate({"language": "fr", "experiences": [{"description": "x"}]})


def test_unknown_keys_are_ignored():
    cv = AdaptedCV.model_validate({"language": "en", "invented_field": 42})

    assert cv.language == ContentLanguage.EN


def test_too_long_summary_is_rejected():
    with pytest.raises(ValidationError):
        AdaptedCV(language=ContentLanguage.FR, summary="x" * 5001)


def test_strict_json_schema_is_usable_by_the_llm():
    schema = to_strict_json_schema(AdaptedCV, exclude_fields=APP_SET_FIELDS)

    assert "schema_version" not in schema["properties"]
    assert "language" not in schema["properties"]
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["AdaptedExperience"]["additionalProperties"] is False
