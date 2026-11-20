import { isAxiosError } from 'axios'
import { api } from './api'

/**
 * The common candidate profile (T-09), mirroring backend/app/schemas/profile.py.
 * Used by US06 (manual entry), US07 (view and edit) and US31 (dashboard).
 * Keep both files in sync. Field-by-field description: docs/PROFIL.md.
 */

export type ContentLanguage = 'fr' | 'en'
export type SkillCategory = 'hard' | 'soft'
export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type LanguageLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | 'native'
export type EducationLevel = 'secondary' | 'associate' | 'bachelor' | 'master' | 'doctorate'
export type EmploymentType =
  'full_time' | 'part_time' | 'internship' | 'apprenticeship' | 'freelance' | 'volunteer'

/** "2021" or "2021-03": as precise as the CV gives it. */
export type PartialDate = string

export type PersonalInfo = {
  full_name: string | null
  headline: string | null
  email: string | null
  phone: string | null
  location: string | null
  links: string[]
}

export type Skill = {
  name: string
  category: SkillCategory
  level: SkillLevel | null
}

export type LanguageSkill = {
  name: string
  /** ISO 639-1 code: "fr", "en", "ar"... */
  code: string | null
  level: LanguageLevel | null
}

type DatedItem = {
  /** Stable id of the entry. Omit it for a new entry: the API generates one. */
  id?: string
  start_date: PartialDate | null
  end_date: PartialDate | null
  is_current: boolean
}

export type Experience = DatedItem & {
  job_title: string
  company: string | null
  location: string | null
  employment_type: EmploymentType | null
  description: string | null
  achievements: string[]
  skills: string[]
}

export type Education = DatedItem & {
  degree: string
  level: EducationLevel | null
  field_of_study: string | null
  institution: string | null
  location: string | null
  description: string | null
}

export type Certification = {
  id?: string
  name: string
  issuer: string | null
  issue_date: PartialDate | null
  url: string | null
}

export type Project = DatedItem & {
  name: string
  description: string | null
  skills: string[]
  url: string | null
}

export type CandidateProfile = {
  schema_version: 1
  language: ContentLanguage
  personal_info: PersonalInfo
  summary: string | null
  skills: Skill[]
  experiences: Experience[]
  education: Education[]
  languages: LanguageSkill[]
  certifications: Certification[]
  projects: Project[]
}

export type ProfileSource = 'cv_analysis' | 'manual'

export type ProfileResponse = {
  profile: CandidateProfile
  source: ProfileSource
  cv_document_id: string | null
  updated_at: string
}

export function emptyProfile(language: ContentLanguage = 'fr'): CandidateProfile {
  return {
    schema_version: 1,
    language,
    personal_info: {
      full_name: null,
      headline: null,
      email: null,
      phone: null,
      location: null,
      links: [],
    },
    summary: null,
    skills: [],
    experiences: [],
    education: [],
    languages: [],
    certifications: [],
    projects: [],
  }
}

/** The candidate's profile, or null if they don't have one yet. */
export async function fetchMyProfile(): Promise<ProfileResponse | null> {
  try {
    const { data } = await api.get<ProfileResponse>('/profile/me')
    return data
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/** Create or replace the candidate's profile. The API returns it normalised. */
export async function saveMyProfile(profile: CandidateProfile): Promise<ProfileResponse> {
  const { data } = await api.put<ProfileResponse>('/profile/me', profile)
  return data
}

// --- French labels for display (US06, US07, US31) ----------------------------

export const SKILL_CATEGORY_LABELS: Record<SkillCategory, string> = {
  hard: 'Compétence technique',
  soft: 'Savoir-être',
}

export const SKILL_LEVEL_LABELS: Record<SkillLevel, string> = {
  beginner: 'Débutant',
  intermediate: 'Intermédiaire',
  advanced: 'Avancé',
  expert: 'Expert',
}

export const LANGUAGE_LEVEL_LABELS: Record<LanguageLevel, string> = {
  A1: 'A1 (débutant)',
  A2: 'A2 (élémentaire)',
  B1: 'B1 (intermédiaire)',
  B2: 'B2 (intermédiaire avancé)',
  C1: 'C1 (avancé)',
  C2: 'C2 (maîtrise)',
  native: 'Langue maternelle',
}

export const EDUCATION_LEVEL_LABELS: Record<EducationLevel, string> = {
  secondary: 'Baccalauréat',
  associate: 'Bac+2 (BTS, DUT)',
  bachelor: 'Bac+3 (Licence)',
  master: "Bac+5 (Master, diplôme d'ingénieur)",
  doctorate: 'Doctorat',
}

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  full_time: 'Temps plein',
  part_time: 'Temps partiel',
  internship: 'Stage',
  apprenticeship: 'Alternance',
  freelance: 'Freelance',
  volunteer: 'Bénévolat',
}
