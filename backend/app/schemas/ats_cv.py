"""US14 - The adapted CV as a complete, ATS-friendly document.

Built by `services/ats_cv_builder.py` from the candidate's profile (every fact: contact
details, dates, employers, degrees...) and the texts adapted by the LLM (headline, summary,
experience wording). The API returns it as is, and the frontend only has to display it.
"""

from pydantic import BaseModel, Field

from app.schemas.shared import ContentLanguage


class CVContact(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class CVSkillGroup(BaseModel):
    label: str
    skills: list[str]


class CVExperienceEntry(BaseModel):
    job_title: str
    company: str | None = None
    location: str | None = None
    period: str | None = None
    description: str | None = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class CVEducationEntry(BaseModel):
    degree: str
    institution: str | None = None
    location: str | None = None
    period: str | None = None
    description: str | None = None


class CVProjectEntry(BaseModel):
    name: str
    period: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class CVCertificationEntry(BaseModel):
    name: str
    issuer: str | None = None
    date: str | None = None


class CVLanguageEntry(BaseModel):
    name: str
    level: str | None = None


class ATSCVDocument(BaseModel):
    """One column, standard section titles, newest entries first."""

    language: ContentLanguage
    contact: CVContact
    summary: str | None = None
    skill_groups: list[CVSkillGroup] = Field(default_factory=list)
    experiences: list[CVExperienceEntry] = Field(default_factory=list)
    projects: list[CVProjectEntry] = Field(default_factory=list)
    education: list[CVEducationEntry] = Field(default_factory=list)
    certifications: list[CVCertificationEntry] = Field(default_factory=list)
    languages: list[CVLanguageEntry] = Field(default_factory=list)
    # Standard section titles in the CV's language, keyed by section id.
    section_titles: dict[str, str]
    # Standard sections the profile has no content for: to complete in the profile.
    missing_sections: list[str] = Field(default_factory=list)
