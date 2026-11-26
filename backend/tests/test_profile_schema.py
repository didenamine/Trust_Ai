"""T-09 - common candidate profile schema."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.profile import CandidateProfile, Experience
from app.schemas.shared import EducationLevel, LanguageLevel, normalize_skill_name

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def minimal(**fields) -> CandidateProfile:
    return CandidateProfile.model_validate({"language": "fr", **fields})


# --- Fixtures (examples shared with the team) ----------------------------------


@pytest.mark.parametrize("name", ["profile_fr.json", "profile_en.json"])
def test_example_profiles_are_valid_and_round_trip(name: str) -> None:
    data = load_fixture(name)

    profile = CandidateProfile.model_validate(data)

    assert profile.model_dump(mode="json") == data


def test_minimal_profile_only_needs_a_language() -> None:
    profile = minimal()

    assert profile.schema_version == 1
    assert profile.skills == []
    assert profile.personal_info.full_name is None


@pytest.mark.parametrize("language", [None, "de", ""])
def test_language_must_be_fr_or_en(language) -> None:
    with pytest.raises(ValidationError):
        CandidateProfile.model_validate({"language": language})


# --- Input from the LLM and from forms --------------------------------------


def test_blank_strings_become_null() -> None:
    profile = minimal(
        summary="  ",
        personal_info={"full_name": "", "email": "", "phone": " "},
        experiences=[{"job_title": "Dev", "company": "", "start_date": ""}],
    )

    assert profile.summary is None
    assert profile.personal_info.email is None
    assert profile.personal_info.phone is None
    assert profile.experiences[0].company is None
    assert profile.experiences[0].start_date is None


def test_unknown_keys_are_ignored() -> None:
    profile = minimal(hobbies=["chess"], skills=[{"name": "Go", "confidence": 0.9}])

    assert "hobbies" not in profile.model_dump()
    assert profile.skills[0].name == "Go"


def test_text_is_trimmed() -> None:
    assert minimal(skills=[{"name": "  React  "}]).skills[0].name == "React"


def test_links_get_a_scheme() -> None:
    profile = minimal(personal_info={"links": ["github.com/me", "https://linkedin.com/in/me"]})

    assert [str(link) for link in profile.personal_info.links] == [
        "https://github.com/me",
        "https://linkedin.com/in/me",
    ]


def test_invalid_email_is_rejected() -> None:
    with pytest.raises(ValidationError):
        minimal(personal_info={"email": "not-an-email"})


@pytest.mark.parametrize("name", ["Jean-Luc O’Brien", "S. Ben Ali", "John Smith Jr."])
def test_full_name_accepts_letters_accents_and_separators(name: str) -> None:
    assert minimal(personal_info={"full_name": name}).personal_info.full_name == name


@pytest.mark.parametrize("name", ["Sarra123", "Sarra_Benali", "123"])
def test_full_name_rejects_non_letters(name: str) -> None:
    with pytest.raises(ValidationError):
        minimal(personal_info={"full_name": name})


@pytest.mark.parametrize(
    "phone",
    ["+216 20 000 000", "+21620000000", "+216-20-000-000", "20 000 000", "0021620000000"],
)
def test_tunisian_phones_are_stored_in_one_format(phone: str) -> None:
    assert minimal(personal_info={"phone": phone}).personal_info.phone == "+216 20 000 000"


@pytest.mark.parametrize("phone", ["+33 6 12 34 56 78", "+1 (415) 555-0100", "+44 20 7946 0958"])
def test_foreign_phones_are_kept_as_written(phone: str) -> None:
    # CVs analysed by US05 can come from anywhere: their phone must not be erased.
    assert minimal(personal_info={"phone": phone}).personal_info.phone == phone


@pytest.mark.parametrize("phone", ["abc", "12 34", "+216 20 000 000 poste 12", "1" * 16])
def test_phone_rejects_what_is_not_a_phone_number(phone: str) -> None:
    with pytest.raises(ValidationError):
        minimal(personal_info={"phone": phone})


def test_required_fields_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        minimal(experiences=[{"job_title": "  "}])


def test_lists_are_capped() -> None:
    with pytest.raises(ValidationError):
        minimal(skills=[{"name": f"skill {i}"} for i in range(151)])


# --- Dates ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2021", "2021"),
        (2021, "2021"),
        ("2021-03", "2021-03"),
        ("2021-3", "2021-03"),
        ("03/2021", "2021-03"),
        ("3.2021", "2021-03"),
        ("2021-03-15", "2021-03"),
        (date(2021, 3, 15), "2021-03"),
    ],
)
def test_dates_are_normalized(raw, expected: str) -> None:
    assert Experience(job_title="Dev", start_date=raw).start_date == expected


@pytest.mark.parametrize("raw", ["2021-13", "21", "mars 2021", "1850", "2021/00"])
def test_invalid_dates_are_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        Experience(job_title="Dev", start_date=raw)


def test_end_date_before_start_date_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Experience(job_title="Dev", start_date="2022-05", end_date="2021")


def test_year_only_dates_in_the_same_year_are_accepted() -> None:
    Experience(job_title="Dev", start_date="2022-05", end_date="2022")


def test_current_position_has_no_end_date() -> None:
    experience = Experience(job_title="Dev", start_date="2022", end_date="2023", is_current=True)

    assert experience.end_date is None


# --- Skills and languages ------------------------------------------------------


def test_duplicate_skills_are_merged_keeping_the_best_level() -> None:
    profile = minimal(
        skills=[
            {"name": "Python", "level": "intermediate"},
            {"name": "python ", "level": "expert"},
            {"name": "PYTHON"},
            {"name": "Réseaux"},
            {"name": "reseaux"},
        ]
    )

    assert [(s.name, s.level) for s in profile.skills] == [
        ("Python", "expert"),
        ("Réseaux", None),
    ]


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("  Node.JS ", "node.js"),
        ("C++", "c++"),
        ("C#", "c#"),
        (".NET", ".net"),
        ("Gestion   de projet", "gestion de projet"),
        ("Sécurité réseau", "securite reseau"),
    ],
)
def test_skill_keys_keep_meaningful_characters(name: str, key: str) -> None:
    assert normalize_skill_name(name) == key


def test_languages_are_merged_by_iso_code() -> None:
    profile = minimal(
        languages=[
            {"name": "Anglais", "code": "EN", "level": "B1"},
            {"name": "English", "code": "en", "level": "C1"},
            {"name": "Espagnol", "code": ""},
        ]
    )

    assert [(lang.name, lang.code, lang.level) for lang in profile.languages] == [
        ("Anglais", "en", LanguageLevel.C1),
        ("Espagnol", None, None),
    ]


def test_skill_keys_include_skills_from_experiences_and_projects() -> None:
    profile = CandidateProfile.model_validate(load_fixture("profile_fr.json"))

    keys = profile.skill_keys()

    assert {"python", "react", "travail en equipe", "llm"} <= keys


# --- Ids -----------------------------------------------------------------------


def test_new_entries_get_unique_ids() -> None:
    profile = minimal(experiences=[{"job_title": "A"}, {"job_title": "B"}])

    ids = [experience.id for experience in profile.experiences]
    assert all(ids) and len(set(ids)) == 2


def test_existing_ids_are_kept_and_duplicates_replaced() -> None:
    profile = minimal(
        experiences=[{"id": "same", "job_title": "A"}, {"id": "same", "job_title": "B"}],
        education=[{"id": "edu-1", "degree": "Licence"}],
    )

    assert profile.experiences[0].id == "same"
    assert profile.experiences[1].id != "same"
    assert profile.education[0].id == "edu-1"


# --- Helpers for matching ------------------------------------------------------


def test_total_experience_counts_overlapping_jobs_once() -> None:
    profile = minimal(
        experiences=[
            {"job_title": "A", "start_date": "2020-01", "end_date": "2020-12"},  # 12 months
            {"job_title": "B", "start_date": "2020-07", "end_date": "2021-06"},  # +6 months
            {"job_title": "C", "start_date": "2023-01", "end_date": "2023-03"},  # +3 months
            {"job_title": "No dates"},
            {"job_title": "No end", "start_date": "2019"},
        ]
    )

    assert profile.total_experience_months() == 21


def test_total_experience_uses_today_for_the_current_job() -> None:
    profile = minimal(experiences=[{"job_title": "A", "start_date": "2025-09", "is_current": True}])

    assert profile.total_experience_months(today=date(2026, 11, 20)) == 15


def test_total_experience_can_exclude_internships_and_skips_volunteering() -> None:
    profile = minimal(
        experiences=[
            {
                "job_title": "Stage",
                "employment_type": "internship",
                "start_date": "2024-01",
                "end_date": "2024-06",
            },
            {
                "job_title": "CDI",
                "employment_type": "full_time",
                "start_date": "2025-01",
                "end_date": "2025-12",
            },
            {
                "job_title": "Bénévole",
                "employment_type": "volunteer",
                "start_date": "2023-01",
                "end_date": "2023-12",
            },
        ]
    )

    assert profile.total_experience_months() == 18
    assert profile.total_experience_months(include_internships=False) == 12


def test_highest_education_level() -> None:
    profile = CandidateProfile.model_validate(load_fixture("profile_en.json"))

    assert profile.highest_education_level() is EducationLevel.MASTER
    assert minimal().highest_education_level() is None


# --- JSON Schema (used to constrain the LLM output in US05) -------------------


def test_json_schema_can_be_generated() -> None:
    schema = CandidateProfile.model_json_schema()

    assert schema["required"] == ["language"]
    assert {"skills", "experiences", "education", "languages"} <= schema["properties"].keys()
