"""US24 - CV-only keyword hygiene.

No target job exists in Sprint 1: keywords are checked for presence, terminology,
action verbs, repetition and specificity, never for job-specific relevance.
"""

from dataclasses import dataclass

from app.schemas.ats import (
    ATSKeywordFinding,
    ATSKeywordKind,
    ATSKeywordSummary,
    ATSLLMKeyword,
    ATSSectionId,
)
from app.schemas.shared import normalize_skill_name
from app.services.ats_sections import SectionContext, section_at_line

_SPECIFIC_KINDS = {
    ATSKeywordKind.HARD_SKILL,
    ATSKeywordKind.TOOL,
    ATSKeywordKind.METHOD,
}
_REPETITION_LIMIT = 4
_MAX_FINDINGS = 150


@dataclass
class KeywordContext:
    summary: ATSKeywordSummary
    findings: list[ATSKeywordFinding]


def _matches(canonical: str, kind: ATSKeywordKind, line: str) -> bool:
    key = normalize_skill_name(canonical)
    value = normalize_skill_name(line)
    if not key or not value:
        return False
    if key in value:
        return True
    if kind == ATSKeywordKind.ACTION_VERB and len(key) >= 5:
        # "manage" should find "managed"; no stemming library needed.
        return key[:-1] in value
    return False


def _line_for(keyword: ATSLLMKeyword, lines: list[str]) -> int | None:
    if (
        keyword.line is not None
        and 1 <= keyword.line <= len(lines)
        and _matches(keyword.canonical, keyword.kind, lines[keyword.line - 1])
    ):
        return keyword.line
    for number, line in enumerate(lines, start=1):
        if _matches(keyword.canonical, keyword.kind, line):
            return number
    return None


def build_keywords(
    text: str, context: SectionContext, llm_keywords: list[ATSLLMKeyword]
) -> KeywordContext:
    lines = text.splitlines()

    merged: dict[tuple[str, ATSKeywordKind], ATSLLMKeyword] = {}
    for keyword in llm_keywords:
        key = (normalize_skill_name(keyword.canonical), keyword.kind)
        existing = merged.get(key)
        if existing is None or keyword.alias_count > existing.alias_count:
            merged[key] = keyword

    findings: list[ATSKeywordFinding] = []
    for keyword in merged.values():
        line = _line_for(keyword, lines)
        occurrences = (
            sum(1 for candidate in lines if _matches(keyword.canonical, keyword.kind, candidate))
            if line is not None
            else 0
        )
        section = section_at_line(context, line)
        if keyword.section is not None and line is not None:
            # Prefer the deterministic line-based section when one was found.
            section = section or keyword.section
        findings.append(
            ATSKeywordFinding(
                canonical=keyword.canonical,
                kind=keyword.kind,
                verified=line is not None,
                line=line,
                section=section,
                occurrences=occurrences,
                alias_count=max(keyword.alias_count, 0),
                in_skills_section=section == ATSSectionId.SKILLS,
                in_context_section=section == ATSSectionId.EXPERIENCE,
            )
        )

    findings.sort(
        key=lambda item: (
            not item.verified,
            item.kind not in _SPECIFIC_KINDS,
            -item.occurrences,
        )
    )
    findings = findings[:_MAX_FINDINGS]

    verified = [item for item in findings if item.verified]
    specific = [item for item in verified if item.kind in _SPECIFIC_KINDS]
    verbs = [item for item in verified if item.kind == ATSKeywordKind.ACTION_VERB]
    generic = [item for item in verified if item.kind == ATSKeywordKind.GENERIC]
    repeated = [item for item in verified if item.occurrences > _REPETITION_LIMIT]

    summary = ATSKeywordSummary(
        specific_count=len(specific),
        action_verb_count=len(verbs),
        generic_count=len(generic),
        verified_count=len(verified),
        repeated_count=len(repeated),
        max_occurrences=max((item.occurrences for item in verified), default=0),
        specificity_ratio=len(specific) / max(1, len(specific) + len(generic)),
        terminology_issues=sum(1 for item in specific if item.alias_count > 0),
    )
    return KeywordContext(summary=summary, findings=findings)
