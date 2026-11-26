"""US14 - Build the adapted CV as a complete, ATS-friendly document.

Everything factual (name, contact details, dates, employers, degrees, languages,
certifications) comes from the candidate's profile, never from the LLM: the LLM only
supplies the adapted wording (headline, summary, order of the skills, text of the
experiences), applied here by experience id. So the CV always has every standard section
the profile can fill, whatever the LLM answered.

ATS rules (same ones the ATS analysis of US24 checks): one column, standard section titles,
newest entries first, plain text, "-" bullets, MM/YYYY dates, skills as short lines.
"""

from collections.abc import Sequence
from typing import Protocol

from app.schemas.ats_cv import (
    ATSCVDocument,
    CVCertificationEntry,
    CVContact,
    CVEducationEntry,
    CVExperienceEntry,
    CVLanguageEntry,
    CVProjectEntry,
    CVSkillGroup,
)
from app.schemas.cv_adaptation import AdaptedCV
from app.schemas.profile import CandidateProfile
from app.schemas.shared import (
    ContentLanguage,
    LanguageLevel,
    Skill,
    SkillCategory,
    normalize_skill_name,
    partial_date_bounds,
)

SECTION_TITLES: dict[ContentLanguage, dict[str, str]] = {
    ContentLanguage.FR: {
        "contact": "Coordonnées",
        "summary": "Profil professionnel",
        "skills": "Compétences",
        "experience": "Expérience professionnelle",
        "projects": "Projets",
        "education": "Formation",
        "certifications": "Certifications",
        "languages": "Langues",
    },
    ContentLanguage.EN: {
        "contact": "Contact",
        "summary": "Professional summary",
        "skills": "Skills",
        "experience": "Professional experience",
        "projects": "Projects",
        "education": "Education",
        "certifications": "Certifications",
        "languages": "Languages",
    },
}

_SKILL_GROUP_LABELS: dict[ContentLanguage, dict[SkillCategory, str]] = {
    ContentLanguage.FR: {
        SkillCategory.HARD: "Compétences techniques",
        SkillCategory.SOFT: "Compétences comportementales",
    },
    ContentLanguage.EN: {
        SkillCategory.HARD: "Technical skills",
        SkillCategory.SOFT: "Soft skills",
    },
}

_PRESENT = {ContentLanguage.FR: "Présent", ContentLanguage.EN: "Present"}
_NATIVE = {ContentLanguage.FR: "Langue maternelle", ContentLanguage.EN: "Native"}
_TECHNOLOGIES = {ContentLanguage.FR: "Technologies : ", ContentLanguage.EN: "Technologies: "}
_COLON = {ContentLanguage.FR: " :", ContentLanguage.EN: ":"}

# The ATS analysis (US24) wants a skills section made of several short lines.
_SKILL_LINE_WIDTH = 45

# Sections reported as "to complete" when the profile has nothing for them. Projects stay
# optional; contact is checked separately (an e-mail or a phone number is enough).
_EXPECTED_SECTIONS = ("summary", "skills", "experience", "education", "certifications", "languages")


class _Dated(Protocol):
    start_date: str | None
    end_date: str | None
    is_current: bool


# --- Dates --------------------------------------------------------------------


def format_date(value: str | None) -> str | None:
    """ "2025-09" -> "09/2025"; "2025" -> "2025"."""
    if not value:
        return None
    year, _, month = value.partition("-")
    return f"{month}/{year}" if month else year


def format_period(item: _Dated, language: ContentLanguage) -> str | None:
    start = format_date(item.start_date)
    end = _PRESENT[language] if item.is_current else format_date(item.end_date)
    if start and end:
        return f"{start} - {end}"
    return start or end


def _sort_key(item: _Dated) -> tuple[int, int, int, int]:
    """Newest first once reversed: the end of the period, then its start."""
    if item.is_current:
        end = (9999, 12)
    elif item.end_date:
        end = partial_date_bounds(item.end_date)[1]
    elif item.start_date:
        end = partial_date_bounds(item.start_date)[1]
    else:
        return (0, 0, 0, 0)  # undated entries go last, in their original order
    start = partial_date_bounds(item.start_date)[0] if item.start_date else (0, 0)
    return (*end, *start)


def _newest_first[D: _Dated](items: Sequence[D]) -> list[D]:
    return sorted(items, key=_sort_key, reverse=True)  # stable: ties keep their order


# --- Document -----------------------------------------------------------------


def build_ats_cv(profile: CandidateProfile, adapted: AdaptedCV) -> ATSCVDocument:
    language = profile.language
    info = profile.personal_info
    adapted_by_id = {item.experience_id: item for item in adapted.experiences}

    contact = CVContact(
        full_name=info.full_name,
        headline=adapted.headline or info.headline,
        email=str(info.email) if info.email else None,
        phone=info.phone,
        location=info.location,
        links=[str(link) for link in info.links],
    )

    experiences = []
    for experience in _newest_first(profile.experiences):
        rewritten = adapted_by_id.get(experience.id)
        experiences.append(
            CVExperienceEntry(
                job_title=experience.job_title,
                company=experience.company,
                location=experience.location,
                period=format_period(experience, language),
                description=(rewritten.description if rewritten else None)
                or experience.description,
                bullets=list(
                    (rewritten.achievements if rewritten else None) or experience.achievements
                ),
                technologies=list(experience.skills),
            )
        )

    education = []
    for item in _newest_first(profile.education):
        degree = item.degree
        if item.field_of_study and item.field_of_study.lower() not in degree.lower():
            degree = f"{degree}, {item.field_of_study}"
        education.append(
            CVEducationEntry(
                degree=degree,
                institution=item.institution,
                location=item.location,
                period=format_period(item, language),
                description=item.description,
            )
        )

    projects = [
        CVProjectEntry(
            name=project.name,
            period=format_period(project, language),
            description=project.description,
            technologies=list(project.skills),
            url=str(project.url) if project.url else None,
        )
        for project in _newest_first(profile.projects)
    ]

    certifications = [
        CVCertificationEntry(
            name=certification.name,
            issuer=certification.issuer,
            date=format_date(certification.issue_date),
        )
        for certification in profile.certifications
    ]

    languages = [
        CVLanguageEntry(name=item.name, level=_language_level(item.level, language))
        for item in profile.languages
    ]

    document = ATSCVDocument(
        language=language,
        contact=contact,
        summary=adapted.summary or profile.summary,
        skill_groups=_skill_groups(profile, adapted, language),
        experiences=experiences,
        projects=projects,
        education=education,
        certifications=certifications,
        languages=languages,
        section_titles=dict(SECTION_TITLES[language]),
    )
    document.missing_sections = _missing_sections(document)
    return document


def _language_level(level: LanguageLevel | None, language: ContentLanguage) -> str | None:
    if level is None:
        return None
    return _NATIVE[language] if level == LanguageLevel.NATIVE else level.value


def _skill_groups(
    profile: CandidateProfile, adapted: AdaptedCV, language: ContentLanguage
) -> list[CVSkillGroup]:
    """The adapted order (most relevant first), split into technical and soft skills.

    Only skills of the profile are kept, with the profile's spelling: a skill the LLM
    added is dropped, one it left out follows in its original order.
    """
    by_key = {skill.key: skill for skill in profile.skills}
    ordered: list[Skill] = []
    seen: set[str] = set()
    for name in adapted.highlighted_skills:
        key = normalize_skill_name(name)
        if key in by_key and key not in seen:
            seen.add(key)
            ordered.append(by_key[key])
    ordered.extend(skill for key, skill in by_key.items() if key not in seen)

    grouped: dict[SkillCategory, list[str]] = {SkillCategory.HARD: [], SkillCategory.SOFT: []}
    for skill in ordered:
        grouped[skill.category].append(skill.name)
    labels = _SKILL_GROUP_LABELS[language]
    return [
        CVSkillGroup(label=labels[category], skills=names)
        for category, names in grouped.items()
        if names
    ]


def _missing_sections(document: ATSCVDocument) -> list[str]:
    filled = {
        "summary": bool(document.summary),
        "skills": bool(document.skill_groups),
        "experience": bool(document.experiences),
        "education": bool(document.education),
        "certifications": bool(document.certifications),
        "languages": bool(document.languages),
    }
    missing = [section for section in _EXPECTED_SECTIONS if not filled[section]]
    if not (document.contact.email or document.contact.phone):
        missing.insert(0, "contact")
    return missing


# --- Plain text ---------------------------------------------------------------


def _wrap_items(items: list[str], width: int = _SKILL_LINE_WIDTH) -> list[str]:
    """Pack skills into short lines, never splitting one skill over two lines."""
    lines: list[str] = []
    current = ""
    for item in items:
        candidate = f"{current}, {item}" if current else item
        if current and len(candidate) + 1 > width:  # +1: the comma ending the line
            lines.append(f"{current},")
            current = item
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _join(*parts: str | None, separator: str = " | ") -> str:
    return separator.join(part for part in parts if part)


def render_ats_text(document: ATSCVDocument) -> str:
    """The CV as plain text, the safest format for an ATS (copy it into any editor)."""
    language = document.language
    titles = document.section_titles
    lines: list[str] = []

    contact = document.contact
    if contact.full_name:
        lines.append(contact.full_name)
    if contact.headline:
        lines.append(contact.headline)
    details = _join(contact.location, contact.phone, contact.email)
    if details:
        lines.append(details)
    lines.extend(contact.links)

    def add_section(key: str, body: list[str]) -> None:
        if body:
            lines.extend(["", titles[key].upper(), *body])

    def blocks(entries: list[list[str]]) -> list[str]:
        body: list[str] = []
        for entry in entries:
            if body:
                body.append("")
            body.extend(entry)
        return body

    add_section("summary", [document.summary] if document.summary else [])

    skills: list[str] = []
    for group in document.skill_groups:
        skills.append(f"{group.label}{_COLON[language]}")
        skills.extend(_wrap_items(group.skills))
    add_section("skills", skills)

    experience_blocks = []
    for experience in document.experiences:
        block = [_join(experience.job_title, experience.company, experience.location)]
        if experience.period:
            block.append(experience.period)
        if experience.description:
            block.append(experience.description)
        block.extend(f"- {bullet}" for bullet in experience.bullets)
        if experience.technologies:
            block.append(_TECHNOLOGIES[language] + ", ".join(experience.technologies))
        experience_blocks.append(block)
    add_section("experience", blocks(experience_blocks))

    project_blocks = []
    for project in document.projects:
        block = [_join(project.name, project.period)]
        if project.description:
            block.append(project.description)
        if project.technologies:
            block.append(_TECHNOLOGIES[language] + ", ".join(project.technologies))
        if project.url:
            block.append(project.url)
        project_blocks.append(block)
    add_section("projects", blocks(project_blocks))

    education_blocks = []
    for item in document.education:
        block = [_join(item.degree, item.institution, item.location)]
        if item.period:
            block.append(item.period)
        if item.description:
            block.append(item.description)
        education_blocks.append(block)
    add_section("education", blocks(education_blocks))

    add_section(
        "certifications",
        [_join(item.name, item.issuer, item.date) for item in document.certifications],
    )

    add_section(
        "languages",
        [f"{item.name} ({item.level})" if item.level else item.name for item in document.languages],
    )

    return "\n".join(lines).strip() + "\n"
