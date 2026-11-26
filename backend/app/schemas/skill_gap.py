"""US33 - Compétences manquantes et prioritaires, agrégées à partir du matching (US12)."""

from app.schemas.shared import SchemaModel, ShortText, SkillCategory


class PrioritizedSkill(SchemaModel):
    name: ShortText
    category: SkillCategory
    missing_in_offers: int
    """How many of the candidate's analysed offers require this skill and it's missing."""


class SkillGapResult(SchemaModel):
    """Sorted by priority: most frequently missing first, hard skills before soft on a tie."""

    skills: list[PrioritizedSkill]
    offers_considered: int
    """How many of the candidate's offers already had an analysis (US09) to compare against."""
