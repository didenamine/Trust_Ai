"""US14 - The adapted CV is a complete, ATS-friendly document built from the profile."""

import json
from pathlib import Path
from typing import Any

from app.schemas.ats import ATSSectionId, ATSStatus
from app.schemas.cv_adaptation import AdaptedCV
from app.schemas.profile import CandidateProfile
from app.services.ats_cv_builder import build_ats_cv, render_ats_text
from app.services.ats_sections import detect_sections

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_profile(**changes: Any) -> CandidateProfile:
    data = json.loads((FIXTURES_DIR / "profile_fr.json").read_text(encoding="utf-8"))
    data.update(changes)
    return CandidateProfile.model_validate(data)


def adapted_cv(**changes: Any) -> AdaptedCV:
    data: dict[str, Any] = {
        "language": "fr",
        "headline": "Développeuse full-stack Python / React",
        "summary": "Développeuse full-stack à l'aise avec Python et React, habituée aux API REST.",
        # "Kubernetes" is not in the profile: it must never reach the CV.
        "highlighted_skills": ["Kubernetes", "Python", "react", "FastAPI"],
        "experiences": [
            {
                "experience_id": "exp-pfe",
                "description": "Développement d'une plateforme web.",
                "achievements": ["Développé une API REST FastAPI de 25 endpoints"],
            }
        ],
        **changes,
    }
    return AdaptedCV.model_validate(data)


def test_every_standard_section_is_filled_from_the_profile() -> None:
    document = build_ats_cv(load_profile(), adapted_cv())

    assert document.contact.full_name == "Sarra Ben Ali"
    assert document.contact.email == "sarra.benali@example.com"
    assert document.contact.headline == "Développeuse full-stack Python / React"
    assert document.summary is not None and "Python et React" in document.summary
    assert document.skill_groups and document.experiences and document.education
    assert document.projects
    assert [item.name for item in document.certifications] == ["Professional Scrum Master I"]
    assert document.certifications[0].date == "11/2024"
    assert [(item.name, item.level) for item in document.languages] == [
        ("Arabe", "Langue maternelle"),
        ("Français", "C1"),
        ("Anglais", "B2"),
    ]
    assert document.missing_sections == []


def test_experiences_are_newest_first_with_the_adapted_wording_by_id() -> None:
    profile = load_profile()
    document = build_ats_cv(profile, adapted_cv())

    current, internship = document.experiences
    assert current.job_title == "Développeuse web"
    assert current.period == "09/2025 - Présent"
    assert internship.period == "02/2025 - 07/2025"

    # Adapted by id...
    assert internship.description == "Développement d'une plateforme web."
    assert internship.bullets == ["Développé une API REST FastAPI de 25 endpoints"]
    # ...and the profile's own wording when the LLM left an experience alone.
    original = next(item for item in profile.experiences if item.id == "exp-dev")
    assert current.description == original.description
    assert current.bullets == original.achievements


def test_education_is_newest_first() -> None:
    document = build_ats_cv(load_profile(), adapted_cv())

    assert document.education[0].degree.startswith("Licence")
    assert document.education[0].period == "2022 - 2025"


def test_only_skills_of_the_profile_are_kept_with_their_spelling() -> None:
    profile = load_profile()
    document = build_ats_cv(profile, adapted_cv())

    listed = [name for group in document.skill_groups for name in group.skills]
    assert document.skill_groups[0].label == "Compétences techniques"
    assert listed[:3] == ["Python", "React", "FastAPI"]
    assert "Kubernetes" not in listed
    assert sorted(listed) == sorted(skill.name for skill in profile.skills)


def test_the_text_is_plain_with_standard_uppercase_titles() -> None:
    text = render_ats_text(build_ats_cv(load_profile(), adapted_cv()))
    lines = text.splitlines()

    for title in (
        "PROFIL PROFESSIONNEL",
        "COMPÉTENCES",
        "EXPÉRIENCE PROFESSIONNELLE",
        "FORMATION",
        "CERTIFICATIONS",
        "LANGUES",
    ):
        assert title in lines
    assert "09/2025 - Présent" in lines
    assert "- Développé une API REST FastAPI de 25 endpoints" in lines
    assert "Kubernetes" not in text


def test_the_text_passes_the_ats_section_check_of_us24() -> None:
    text = render_ats_text(build_ats_cv(load_profile(), adapted_cv()))

    findings = {finding.section: finding for finding in detect_sections(text).findings}
    for section in ATSSectionId:
        assert findings[section].present, section
        assert findings[section].status == ATSStatus.OK, (section, findings[section].issues)


def test_titles_and_labels_follow_the_language_of_the_profile() -> None:
    document = build_ats_cv(load_profile(language="en"), adapted_cv(language="en"))
    text = render_ats_text(document)

    assert document.section_titles["experience"] == "Professional experience"
    assert "PROFESSIONAL EXPERIENCE" in text.splitlines()
    assert "09/2025 - Present" in text.splitlines()
    assert ("Arabe", "Native") in [(item.name, item.level) for item in document.languages]


def test_sections_the_profile_cannot_fill_are_reported_and_left_out() -> None:
    profile = load_profile(education=[], certifications=[], languages=[])
    document = build_ats_cv(profile, adapted_cv())
    text = render_ats_text(document)

    assert document.missing_sections == ["education", "certifications", "languages"]
    assert "FORMATION" not in text.splitlines()
    assert "LANGUES" not in text.splitlines()


def test_missing_contact_details_are_reported_first() -> None:
    profile = load_profile()
    profile.personal_info.email = None
    profile.personal_info.phone = None

    document = build_ats_cv(profile, adapted_cv())

    assert document.missing_sections[0] == "contact"
