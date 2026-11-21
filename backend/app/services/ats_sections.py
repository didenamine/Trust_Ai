"""US24 - deterministic CV section detection.

Aliases are matched against a normalised (accent-free, lowercase) heading line.
Only stable canonical ids, check codes and line numbers are returned: no CV text is
ever copied into the ATS result.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.schemas.ats import (
    ATSLLMSection,
    ATSSectionFinding,
    ATSSectionId,
    ATSStatus,
)

REQUIRED_SECTIONS = (
    ATSSectionId.CONTACT,
    ATSSectionId.EXPERIENCE,
    ATSSectionId.EDUCATION,
    ATSSectionId.SKILLS,
)
OPTIONAL_SECTIONS = (
    ATSSectionId.SUMMARY,
    ATSSectionId.CERTIFICATIONS,
    ATSSectionId.LANGUAGES,
)

_ALIASES: dict[ATSSectionId, tuple[str, ...]] = {
    ATSSectionId.CONTACT: (
        "contact",
        "coordonnees",
        "coordonnees professionnelles",
        "contact details",
        "personal information",
    ),
    ATSSectionId.SUMMARY: (
        "profil",
        "profil professionnel",
        "resume",
        "resume professionnel",
        "a propos",
        "about",
        "about me",
        "summary",
        "professional summary",
        "profile",
    ),
    ATSSectionId.EXPERIENCE: (
        "experience",
        "experiences",
        "experience professionnelle",
        "experiences professionnelles",
        "parcours professionnel",
        "parcours",
        "work experience",
        "work history",
        "employment history",
        "employment",
        "professional experience",
    ),
    ATSSectionId.EDUCATION: (
        "formation",
        "formations",
        "scolarite",
        "etudes",
        "diplomes",
        "education",
        "education and training",
        "academic background",
        "academic qualifications",
    ),
    ATSSectionId.SKILLS: (
        "competence",
        "competences",
        "competences techniques",
        "competences clefs",
        "skills",
        "technical skills",
        "hard skills",
        "key skills",
        "tools",
        "outils",
    ),
    ATSSectionId.CERTIFICATIONS: (
        "certification",
        "certifications",
        "certificat",
        "certificats",
        "certificates",
        "licence",
        "licences",
        "diplomes et certifications",
    ),
    ATSSectionId.LANGUAGES: (
        "langue",
        "langues",
        "langues parlees",
        "language",
        "languages",
        "language skills",
    ),
}


def _normalize_alias(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.strip().lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9&/+\-]+", " ", value)
    return " ".join(value.split())


_NORMALIZED_ALIASES = {
    section: {_normalize_alias(alias) for alias in aliases} for section, aliases in _ALIASES.items()
}

_LEADING_MARKER_RE = re.compile(r"^(?:[-•*·]\s*|\d+[.)]\s*)")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(
    r"(?:\+[\d\s().\-/]{7,20}|\b0[\d\s().\-/]{8,20}|\b\d{2}[ .-]?\d{3}[ .-]?\d{3}\b)"
)
_LINK_RE = re.compile(r"(?:https?://|www\.|linkedin\.com|github\.com)", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_CURRENT_RE = re.compile(r"\b(present|now|current|aujourd'hui|en cours|actuel)\b", re.IGNORECASE)
_CEFR_RE = re.compile(
    r"\b(?:A1|A2|B1|B2|C1|C2|native|maternelle|courant|intermediaire|fluent)\b", re.IGNORECASE
)


@dataclass
class SectionContext:
    findings: list[ATSSectionFinding]
    ranges: dict[ATSSectionId, tuple[int, int]]
    line_count: int

    def content_lines(self, section: ATSSectionId) -> list[str]:
        span = self.ranges.get(section)
        if span is None:
            return []
        return self._content_lines[section]

    # Filled after construction by `detect_sections` (kept out of the schema).
    _content_lines: dict[ATSSectionId, list[str]] = None  # type: ignore[assignment]


def _heading_key(line: str) -> str:
    stripped = line.strip()
    if not stripped or len(stripped) > 70 or stripped.endswith("."):
        return ""
    stripped = _LEADING_MARKER_RE.sub("", stripped).strip().rstrip(":").strip()
    if not stripped or stripped.endswith("."):
        return ""
    return _normalize_alias(stripped)


def _detect_heading(line: str) -> ATSSectionId | None:
    key = _heading_key(line)
    if not key:
        return None
    for section, aliases in _NORMALIZED_ALIASES.items():
        if key in aliases:
            return section
    return None


def _digit_count(value: str) -> int:
    return sum(char.isdigit() for char in value)


def _contact_checks(lines: list[str]) -> dict[str, bool]:
    email = phone = link = False
    for line in lines:
        if not email and _EMAIL_RE.search(line):
            email = True
        if not phone:
            for match in _PHONE_RE.finditer(line):
                if 8 <= _digit_count(match.group(0)) <= 15:
                    phone = True
                    break
        if not link and _LINK_RE.search(line):
            link = True
    return {"has_email": email, "has_phone": phone, "has_link": link}


def _content_checks(section: ATSSectionId, lines: list[str]) -> dict[str, bool]:
    content = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith(("-", "•", "*"))
    ]
    joined = "\n".join(content)
    checks: dict[str, bool] = {"has_entries": bool(content)}
    if section == ATSSectionId.EXPERIENCE:
        checks["has_dates"] = bool(_YEAR_RE.search(joined) or _CURRENT_RE.search(joined))
        checks["has_multiple_entries"] = len(content) >= 3
    elif section == ATSSectionId.EDUCATION:
        checks["has_dates"] = bool(_YEAR_RE.search(joined))
        checks["has_entries"] = len(content) >= 1
    elif section == ATSSectionId.SKILLS:
        checks["has_skill_list"] = sum(1 for line in content if len(line) <= 60) >= 3
    elif section == ATSSectionId.SUMMARY:
        checks["is_concise"] = 5 <= len(joined.split()) <= 150
    elif section == ATSSectionId.LANGUAGES:
        checks["has_level"] = bool(_CEFR_RE.search(joined))
    elif section == ATSSectionId.CERTIFICATIONS:
        checks["has_entries"] = len(content) >= 1
    return checks


def _issues_for(section: ATSSectionId, checks: dict[str, bool]) -> list[str]:
    issues: list[str] = []
    if not checks.get("has_entries", True):
        issues.append("section.no_content")
    if section == ATSSectionId.EXPERIENCE and not checks.get("has_dates", True):
        issues.append("section.experience.no_dates")
    if section == ATSSectionId.EDUCATION and not checks.get("has_dates", True):
        issues.append("section.education.no_dates")
    if section == ATSSectionId.SKILLS and not checks.get("has_skill_list", True):
        issues.append("section.skills.too_few_skills")
    if section == ATSSectionId.SUMMARY and not checks.get("is_concise", True):
        issues.append("section.summary.not_concise")
    if section == ATSSectionId.LANGUAGES and not checks.get("has_level", True):
        issues.append("section.languages.no_level")
    return issues


def _status(section: ATSSectionId, present: bool, issues: list[str]) -> ATSStatus:
    if not present:
        return ATSStatus.MISSING if section in REQUIRED_SECTIONS else ATSStatus.NA
    if issues:
        return ATSStatus.WARNING
    return ATSStatus.OK


def detect_sections(text: str, llm_sections: list[ATSLLMSection] | None = None) -> SectionContext:
    """Detect standard CV sections without relying on the profile table."""
    lines = text.splitlines()
    line_count = len(lines)

    headings: dict[ATSSectionId, int] = {}
    detections: dict[ATSSectionId, str] = {}
    for number, line in enumerate(lines, start=1):
        section = _detect_heading(line)
        if section is not None and section not in headings:
            headings[section] = number
            detections[section] = "heading_alias"

    # The LLM resolves unusual headings, but only at a line that exists in the CV.
    for suggestion in llm_sections or []:
        line = suggestion.line
        if suggestion.section in headings or line is None or not 1 <= line <= line_count:
            continue
        if suggestion.confidence < 0.5:
            continue
        headings[suggestion.section] = line
        detections[suggestion.section] = "llm"

    contact_checks = _contact_checks(lines)
    if ATSSectionId.CONTACT not in headings:
        contact_line = next(
            (number for number, line in enumerate(lines, start=1) if _EMAIL_RE.search(line)),
            None,
        )
        if contact_line is not None:
            headings[ATSSectionId.CONTACT] = contact_line
            detections[ATSSectionId.CONTACT] = "contact_signals"

    ordered = sorted(headings.items(), key=lambda item: item[1])
    ranges: dict[ATSSectionId, tuple[int, int]] = {}
    for index, (section, line) in enumerate(ordered):
        end = ordered[index + 1][1] - 1 if index + 1 < len(ordered) else line_count
        if section == ATSSectionId.CONTACT and line > 1:
            # Contact details usually sit above the first heading.
            line = 1
        ranges[section] = (max(line, 1), max(end, line))

    content_lines: dict[ATSSectionId, list[str]] = {}
    for section, (start, end) in ranges.items():
        # Exclude the heading itself from "content" checks.
        content_start = start + 1 if section != ATSSectionId.CONTACT else start
        content_lines[section] = lines[content_start - 1 : min(end, line_count)]

    findings: list[ATSSectionFinding] = []
    for index, (section, line) in enumerate(ordered):
        content = content_lines.get(section, [])
        checks = _content_checks(section, content)
        if section == ATSSectionId.CONTACT:
            checks = {**contact_checks, "has_entries": any(contact_checks.values())}
        issues = _issues_for(section, checks)
        findings.append(
            ATSSectionFinding(
                section=section,
                status=_status(section, True, issues),
                present=True,
                detection=detections.get(section, "unknown"),
                line=line,
                order_index=index,
                checks=checks,
                issues=issues,
            )
        )

    for section in (*REQUIRED_SECTIONS, *OPTIONAL_SECTIONS):
        if section in headings:
            continue
        findings.append(
            ATSSectionFinding(
                section=section,
                status=_status(section, False, []),
                present=False,
                detection="none",
                checks={},
                issues=[] if section in OPTIONAL_SECTIONS else ["section.missing"],
            )
        )

    context = SectionContext(findings=findings, ranges=ranges, line_count=line_count)
    context._content_lines = content_lines
    return context


def section_at_line(context: SectionContext, line: int | None) -> ATSSectionId | None:
    """Return the canonical section containing a 1-based line number."""
    if line is None:
        return None
    for section, (start, end) in sorted(
        context.ranges.items(), key=lambda item: item[1][0], reverse=True
    ):
        if start <= line <= end:
            return section
    return None
