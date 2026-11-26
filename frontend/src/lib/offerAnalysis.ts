import type {
  ContentLanguage,
  EducationLevel,
  EmploymentType,
  SkillCategory,
  SkillLevel,
} from './profile'

/**
 * US09 - requirements extracted from a job offer.
 *
 * Same shape and enums as the candidate profile (see `lib/profile.ts`), but the
 * values describe what an employer asks for, not what a candidate actually has.
 * Keep in sync with `backend/app/schemas/offer_analysis.py`.
 */
export type RequiredSkill = {
  name: string
  category: SkillCategory
  /** Required proficiency when the offer states one explicitly. */
  level: SkillLevel | null
}

export type ExperienceRequirement = {
  min_years: number | null
  max_years: number | null
  job_title: string | null
  employment_type: EmploymentType | null
  description: string | null
  skills: string[]
}

export type EducationRequirement = {
  level: EducationLevel | null
  degree: string | null
  field_of_study: string | null
  description: string | null
}

export type OfferRequirements = {
  schema_version: 1
  language: ContentLanguage
  job_title: string | null
  skills: RequiredSkill[]
  experiences: ExperienceRequirement[]
  education: EducationRequirement[]
}

export type OfferAnalysis = {
  id: string
  offer_id: string
  requirements: OfferRequirements
  created_at: string
  updated_at: string
}
