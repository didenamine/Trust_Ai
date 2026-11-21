"""US24 - transparent, normalised ATS score.

Weights: readability 40 / sections 35 / keywords 25. Optional sections marked N/A
are excluded from the denominator, so their absence never penalises a candidate.
"""

from app.schemas.ats import (
    ATSBand,
    ATSCriterion,
    ATSReadabilityFinding,
    ATSScoreBreakdown,
    ATSSectionFinding,
    ATSSectionId,
    ATSStatus,
)
from app.services.ats_keywords import KeywordContext

READABILITY_WEIGHT = 40
SECTIONS_WEIGHT = 35
KEYWORDS_WEIGHT = 25

SECTION_WEIGHTS: dict[ATSSectionId, int] = {
    ATSSectionId.CONTACT: 8,
    ATSSectionId.EXPERIENCE: 8,
    ATSSectionId.EDUCATION: 6,
    ATSSectionId.SKILLS: 6,
    ATSSectionId.SUMMARY: 3,
    ATSSectionId.CERTIFICATIONS: 2,
    ATSSectionId.LANGUAGES: 2,
}

READABILITY_WEIGHTS = {
    "text_integrity": 12,
    "reading_order": 10,
    "layout": 8,
    "accessibility": 10,
}

KEYWORD_WEIGHTS = {
    "specificity": 9,
    "placement": 8,
    "terminology": 5,
    "repetition": 3,
}

_READABILITY_CODES: dict[str, str] = {
    "pdf.image_only_page": "text_integrity",
    "pdf.multi_column": "layout",
    "docx.multi_column_section": "layout",
    "docx.body_only_tables": "layout",
    "common.text_truncated": "layout",
    "docx.textbox_content_not_extracted": "accessibility",
    "common.contact_in_header_only": "accessibility",
    "docx.images_detected": "accessibility",
}

_SECTION_CHECKS: dict[ATSSectionId, dict[str, float]] = {
    ATSSectionId.CONTACT: {"has_email": 0.5, "has_phone": 0.3, "has_link": 0.2},
    ATSSectionId.EXPERIENCE: {
        "has_entries": 0.3,
        "has_dates": 0.4,
        "has_multiple_entries": 0.3,
    },
    ATSSectionId.EDUCATION: {"has_entries": 0.5, "has_dates": 0.5},
    ATSSectionId.SKILLS: {"has_entries": 0.2, "has_skill_list": 0.8},
    ATSSectionId.SUMMARY: {"has_entries": 0.3, "is_concise": 0.7},
    ATSSectionId.CERTIFICATIONS: {"has_entries": 1.0},
    ATSSectionId.LANGUAGES: {"has_entries": 0.6, "has_level": 0.4},
}


def _round(value: float) -> float:
    return round(max(value, 0.0), 2)


def _status_for_ratio(ratio: float) -> ATSStatus:
    if ratio >= 0.8:
        return ATSStatus.OK
    if ratio > 0:
        return ATSStatus.WARNING
    return ATSStatus.MISSING


def _criterion(
    key: str,
    label_key: str,
    weight: int,
    points: float,
    *,
    status: ATSStatus | None = None,
    applicable: bool = True,
    reason_code: str | None = None,
) -> ATSCriterion:
    return ATSCriterion(
        key=key,
        label_key=label_key,
        weight=weight,
        points=_round(points),
        status=status or _status_for_ratio(points / weight if weight else 0),
        applicable=applicable,
        reason_code=reason_code,
    )


def _section_criteria(
    findings: list[ATSSectionFinding],
) -> tuple[list[ATSCriterion], list[ATSSectionId]]:
    criteria: list[ATSCriterion] = []
    na_sections: list[ATSSectionId] = []
    by_section = {finding.section: finding for finding in findings}

    for section, weight in SECTION_WEIGHTS.items():
        finding = by_section.get(section)
        if finding is None or finding.status == ATSStatus.NA:
            na_sections.append(section)
            criteria.append(
                _criterion(
                    key=f"sections.{section.value}",
                    label_key=f"ats.criterion.section.{section.value}",
                    weight=weight,
                    points=0,
                    status=ATSStatus.NA,
                    applicable=False,
                    reason_code="section.na",
                )
            )
            continue

        if not finding.present or finding.status == ATSStatus.MISSING:
            criteria.append(
                _criterion(
                    key=f"sections.{section.value}",
                    label_key=f"ats.criterion.section.{section.value}",
                    weight=weight,
                    points=0,
                    status=ATSStatus.MISSING,
                    reason_code=finding.issues[0] if finding.issues else "section.missing",
                )
            )
            continue

        checks = finding.checks
        ratio = sum(share for key, share in _SECTION_CHECKS[section].items() if checks.get(key))
        points = ratio * weight
        reason = finding.issues[0] if finding.issues else None
        criteria.append(
            _criterion(
                key=f"sections.{section.value}",
                label_key=f"ats.criterion.section.{section.value}",
                weight=weight,
                points=points,
                status=ATSStatus.WARNING if ratio < 1 else ATSStatus.OK,
                reason_code=reason,
            )
        )
    return criteria, na_sections


def _readability_criteria(readability: list[ATSReadabilityFinding]) -> list[ATSCriterion]:
    deductions: dict[str, float] = {key: 0.0 for key in READABILITY_WEIGHTS}
    codes: dict[str, list[str]] = {key: [] for key in READABILITY_WEIGHTS}

    for finding in readability:
        key = _READABILITY_CODES.get(finding.code, "layout")
        deductions[key] += finding.deduction
        codes[key].append(finding.code)

    criteria: list[ATSCriterion] = []
    for key, weight in READABILITY_WEIGHTS.items():
        points = max(0.0, weight - min(deductions[key], weight))
        # Informational/warning findings without evidence of degraded extraction do
        # not affect the score (Sprint 1 decision).
        status = ATSStatus.WARNING if deductions[key] > 0 else ATSStatus.OK
        reason = next(
            (code for finding in readability if (code := finding.code) in codes[key]), None
        )
        criteria.append(
            _criterion(
                key=f"readability.{key}",
                label_key=f"ats.criterion.readability.{key}",
                weight=weight,
                points=points,
                status=status,
                reason_code=reason,
            )
        )
    return criteria


def _keyword_criteria(keywords: KeywordContext) -> list[ATSCriterion]:
    summary = keywords.summary
    specific = summary.specific_count

    specificity = min(specific / 8, 1.0)
    placement_ratio = (
        sum(
            int(item.in_skills_section) + int(item.in_context_section)
            for item in keywords.findings
            if item.kind.value in {"hard_skill", "tool", "method"}
        )
        / (2 * specific)
        if specific
        else 0.0
    )
    terminology = 1 - min(summary.terminology_issues / max(specific, 1), 1.0) if specific else 0.0
    repetition = (
        1 - min(summary.repeated_count / max(summary.verified_count, 1), 1.0)
        if summary.verified_count
        else 0.0
    )

    ratios = {
        "specificity": specificity,
        "placement": min(placement_ratio, 1.0),
        "terminology": terminology,
        "repetition": repetition,
    }
    reasons = {
        "specificity": "keywords.no_specific_terms" if not specific else None,
        "placement": "keywords.no_placement" if specific and not placement_ratio else None,
        "terminology": "keywords.variant_terminology" if summary.terminology_issues else None,
        "repetition": "keywords.repetition" if summary.repeated_count else None,
    }

    return [
        _criterion(
            key=f"keywords.{key}",
            label_key=f"ats.criterion.keywords.{key}",
            weight=KEYWORD_WEIGHTS[key],
            points=ratios[key] * KEYWORD_WEIGHTS[key],
            status=_status_for_ratio(ratios[key]),
            reason_code=reasons[key],
        )
        for key in KEYWORD_WEIGHTS
    ]


def _band(total: int) -> ATSBand:
    if total >= 90:
        return ATSBand.EXCELLENT
    if total >= 70:
        return ATSBand.GOOD
    if total >= 40:
        return ATSBand.TO_IMPROVE
    return ATSBand.LOW


def compute_score(
    *,
    sections: list[ATSSectionFinding],
    keywords: KeywordContext,
    readability: list[ATSReadabilityFinding],
    scoring_version: int,
) -> ATSScoreBreakdown:
    section_criteria, na_sections = _section_criteria(sections)
    readability_criteria = _readability_criteria(readability)
    keyword_criteria = _keyword_criteria(keywords)

    section_points = sum(item.points for item in section_criteria if item.applicable)
    readability_points = sum(item.points for item in readability_criteria)
    keyword_points = sum(item.points for item in keyword_criteria)
    obtained = section_points + readability_points + keyword_points

    section_weight = sum(item.weight for item in section_criteria if item.applicable)
    denominator = READABILITY_WEIGHT + section_weight + KEYWORDS_WEIGHT
    total = max(0, min(round(100 * obtained / denominator), 100))

    dimensions = [
        _criterion(
            key="readability",
            label_key="ats.dimension.readability",
            weight=READABILITY_WEIGHT,
            points=readability_points,
        ),
        _criterion(
            key="sections",
            label_key="ats.dimension.sections",
            weight=section_weight,
            points=section_points,
        ),
        _criterion(
            key="keywords",
            label_key="ats.dimension.keywords",
            weight=KEYWORDS_WEIGHT,
            points=keyword_points,
        ),
    ]

    return ATSScoreBreakdown(
        total=total,
        band=_band(total),
        scoring_version=scoring_version,
        denominator=denominator,
        dimensions=dimensions,
        criteria=[*readability_criteria, *section_criteria, *keyword_criteria],
        na_sections=na_sections,
    )
