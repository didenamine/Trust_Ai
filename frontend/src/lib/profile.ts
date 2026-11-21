import { isAxiosError } from 'axios'
import { z } from 'zod'
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

// --- Manual entry / US07 form -------------------------------------------------
// The form state mirrors CandidateProfile 1:1, with "" standing for null and ""
// for an unset enum. Conversions below are the only bridge to the common model.

export const CONTENT_LANGUAGE_VALUES = ['fr', 'en'] as const
export const SKILL_CATEGORY_VALUES = ['hard', 'soft'] as const
export const SKILL_LEVEL_VALUES = ['beginner', 'intermediate', 'advanced', 'expert'] as const
export const LANGUAGE_LEVEL_VALUES = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'native'] as const
export const EDUCATION_LEVEL_VALUES = [
  'secondary',
  'associate',
  'bachelor',
  'master',
  'doctorate',
] as const
export const EMPLOYMENT_TYPE_VALUES = [
  'full_time',
  'part_time',
  'internship',
  'apprenticeship',
  'freelance',
  'volunteer',
] as const

const PARTIAL_DATE_RE = /^(19|20)\d{2}(-(0[1-9]|1[0-2]))?$/
const LANGUAGE_CODE_RE = /^[a-z]{2}$/
const FULL_NAME_RE = /^[\p{L}\p{M}][\p{L}\p{M} '\-’.]*$/u
const TUNISIAN_PHONE_RE = /^\+216 \d{2} \d{3} \d{3}$/
// Foreign numbers, e.g. from an analysed CV (US05): +33 6 12 34 56 78, +1 (415) 555-0100.
const INTERNATIONAL_PHONE_RE = /^\+(?!216)\d[\d\s().\-/]{6,24}$/

/** The backend accepts bare domains ("github.com/me") and adds https itself. */
export function normalizeProfileUrl(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
}

function isProfileUrl(value: string): boolean {
  try {
    new URL(normalizeProfileUrl(value))
    return true
  } catch {
    return false
  }
}

const requiredText = (max: number, label: string) =>
  z.string().trim().min(1, `${label} requis`).max(max, `${max} caractères maximum`)

const optionalText = (max: number) => z.string().trim().max(max, `${max} caractères maximum`)

const optionalFullName = optionalText(200).refine(
  (value) => value === '' || FULL_NAME_RE.test(value),
  'Le nom complet ne doit contenir que des lettres',
)

const optionalPhone = optionalText(50).refine(
  (value) => value === '' || TUNISIAN_PHONE_RE.test(value) || INTERNATIONAL_PHONE_RE.test(value),
  'Format attendu : +216 00 000 000',
)

const optionalDate = z
  .string()
  .trim()
  .refine(
    (value) => value === '' || PARTIAL_DATE_RE.test(value),
    'Format attendu : AAAA ou AAAA-MM',
  )

const optionalEmail = z
  .string()
  .trim()
  .max(200)
  .refine(
    (value) => value === '' || z.string().email().safeParse(value).success,
    'Adresse e-mail invalide',
  )

const optionalUrl = z
  .string()
  .trim()
  .max(200, '200 caractères maximum')
  .refine((value) => value === '' || isProfileUrl(value), 'URL invalide')

const requiredUrl = z
  .string()
  .trim()
  .max(200, '200 caractères maximum')
  .refine((value) => isProfileUrl(value), 'URL invalide')

function monthIndex(value: string, edge: 'start' | 'end'): number {
  const [year, month] = value.split('-')
  return Number(year) * 12 + (month ? Number(month) : edge === 'start' ? 1 : 12)
}

const checkPeriod = (
  value: { start_date: string; end_date: string; is_current: boolean },
  ctx: z.RefinementCtx,
) => {
  if (value.is_current && value.end_date) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['end_date'],
      message: 'Une activité en cours ne peut pas avoir de date de fin',
    })
  }
  if (
    !value.is_current &&
    value.start_date &&
    value.end_date &&
    monthIndex(value.end_date, 'end') < monthIndex(value.start_date, 'start')
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['end_date'],
      message: 'La date de fin est antérieure à la date de début',
    })
  }
}

const skillFormSchema = z.object({
  name: requiredText(200, 'Compétence'),
  category: z.enum(SKILL_CATEGORY_VALUES),
  level: z.union([z.literal(''), z.enum(SKILL_LEVEL_VALUES)]),
})

const experienceFormSchema = z
  .object({
    id: z.string().optional(),
    job_title: requiredText(200, 'Intitulé du poste'),
    company: optionalText(200),
    location: optionalText(200),
    employment_type: z.union([z.literal(''), z.enum(EMPLOYMENT_TYPE_VALUES)]),
    start_date: optionalDate,
    end_date: optionalDate,
    is_current: z.boolean(),
    description: optionalText(5000),
    achievements: z.array(requiredText(500, 'Réalisation')).max(20, '20 réalisations maximum'),
    skills: z.array(requiredText(200, 'Compétence')).max(50, '50 compétences maximum'),
  })
  .superRefine(checkPeriod)

const educationFormSchema = z
  .object({
    id: z.string().optional(),
    degree: requiredText(200, 'Diplôme'),
    level: z.union([z.literal(''), z.enum(EDUCATION_LEVEL_VALUES)]),
    field_of_study: optionalText(200),
    institution: optionalText(200),
    location: optionalText(200),
    start_date: optionalDate,
    end_date: optionalDate,
    is_current: z.boolean(),
    description: optionalText(5000),
  })
  .superRefine(checkPeriod)

const languageFormSchema = z.object({
  name: requiredText(200, 'Langue'),
  code: z
    .string()
    .trim()
    .refine(
      (value) => value === '' || LANGUAGE_CODE_RE.test(value),
      'Code ISO 639-1 à deux lettres (ex. fr)',
    ),
  level: z.union([z.literal(''), z.enum(LANGUAGE_LEVEL_VALUES)]),
})

const certificationFormSchema = z.object({
  id: z.string().optional(),
  name: requiredText(200, 'Certification'),
  issuer: optionalText(200),
  issue_date: optionalDate,
  url: optionalUrl,
})

const projectFormSchema = z
  .object({
    id: z.string().optional(),
    name: requiredText(200, 'Projet'),
    description: optionalText(5000),
    start_date: optionalDate,
    end_date: optionalDate,
    is_current: z.boolean(),
    skills: z.array(requiredText(200, 'Compétence')).max(50, '50 compétences maximum'),
    url: optionalUrl,
  })
  .superRefine(checkPeriod)

export const profileFormSchema = z.object({
  schema_version: z.literal(1),
  language: z.enum(CONTENT_LANGUAGE_VALUES),
  personal_info: z.object({
    full_name: optionalFullName,
    headline: optionalText(200),
    email: optionalEmail,
    phone: optionalPhone,
    location: optionalText(200),
    links: z.array(requiredUrl).max(10, '10 liens maximum'),
  }),
  summary: optionalText(5000),
  skills: z.array(skillFormSchema).max(150, '150 compétences maximum'),
  experiences: z.array(experienceFormSchema).max(50, '50 expériences maximum'),
  education: z.array(educationFormSchema).max(30, '30 formations maximum'),
  languages: z.array(languageFormSchema).max(20, '20 langues maximum'),
  certifications: z.array(certificationFormSchema).max(50, '50 certifications maximum'),
  projects: z.array(projectFormSchema).max(50, '50 projets maximum'),
})

/** Form state for the common profile. Only used by the US06 / US07 form. */
export type ProfileFormValues = z.input<typeof profileFormSchema>

const formText = (value: string | null | undefined): string => (value ?? '').trim()
const formNullable = (value: string): string | null => {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

export function emptyProfileForm(): ProfileFormValues {
  return profileToFormValues(emptyProfile())
}

export function profileToFormValues(profile: CandidateProfile): ProfileFormValues {
  return {
    schema_version: 1,
    language: profile.language,
    personal_info: {
      full_name: formText(profile.personal_info.full_name),
      headline: formText(profile.personal_info.headline),
      email: formText(profile.personal_info.email),
      phone: formText(profile.personal_info.phone),
      location: formText(profile.personal_info.location),
      links: profile.personal_info.links.map((link) => String(link)),
    },
    summary: formText(profile.summary),
    skills: profile.skills.map((skill) => ({
      name: skill.name,
      category: skill.category,
      level: skill.level ?? '',
    })),
    experiences: profile.experiences.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      job_title: item.job_title,
      company: formText(item.company),
      location: formText(item.location),
      employment_type: item.employment_type ?? '',
      start_date: formText(item.start_date),
      end_date: formText(item.end_date),
      is_current: item.is_current,
      description: formText(item.description),
      achievements: item.achievements,
      skills: item.skills,
    })),
    education: profile.education.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      degree: item.degree,
      level: item.level ?? '',
      field_of_study: formText(item.field_of_study),
      institution: formText(item.institution),
      location: formText(item.location),
      start_date: formText(item.start_date),
      end_date: formText(item.end_date),
      is_current: item.is_current,
      description: formText(item.description),
    })),
    languages: profile.languages.map((item) => ({
      name: item.name,
      code: formText(item.code),
      level: item.level ?? '',
    })),
    certifications: profile.certifications.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      name: item.name,
      issuer: formText(item.issuer),
      issue_date: formText(item.issue_date),
      url: formText(item.url),
    })),
    projects: profile.projects.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      name: item.name,
      description: formText(item.description),
      start_date: formText(item.start_date),
      end_date: formText(item.end_date),
      is_current: item.is_current,
      skills: item.skills,
      url: formText(item.url),
    })),
  }
}

/** Convert the form state back into the one and only CandidateProfile model. */
export function formValuesToProfile(values: ProfileFormValues): CandidateProfile {
  return {
    schema_version: 1,
    language: values.language,
    personal_info: {
      full_name: formNullable(values.personal_info.full_name),
      headline: formNullable(values.personal_info.headline),
      email: formNullable(values.personal_info.email),
      phone: formNullable(values.personal_info.phone),
      location: formNullable(values.personal_info.location),
      links: values.personal_info.links.map(normalizeProfileUrl).filter(Boolean),
    },
    summary: formNullable(values.summary),
    skills: values.skills.map((skill) => ({
      name: skill.name.trim(),
      category: skill.category,
      level: skill.level === '' ? null : skill.level,
    })),
    experiences: values.experiences.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      job_title: item.job_title.trim(),
      company: formNullable(item.company),
      location: formNullable(item.location),
      employment_type: item.employment_type === '' ? null : item.employment_type,
      start_date: formNullable(item.start_date),
      end_date: formNullable(item.end_date),
      is_current: item.is_current,
      description: formNullable(item.description),
      achievements: item.achievements.map((value) => value.trim()).filter(Boolean),
      skills: item.skills.map((value) => value.trim()).filter(Boolean),
    })),
    education: values.education.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      degree: item.degree.trim(),
      level: item.level === '' ? null : item.level,
      field_of_study: formNullable(item.field_of_study),
      institution: formNullable(item.institution),
      location: formNullable(item.location),
      start_date: formNullable(item.start_date),
      end_date: formNullable(item.end_date),
      is_current: item.is_current,
      description: formNullable(item.description),
    })),
    languages: values.languages.map((item) => ({
      name: item.name.trim(),
      code: formNullable(item.code.toLowerCase()),
      level: item.level === '' ? null : item.level,
    })),
    certifications: values.certifications.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      name: item.name.trim(),
      issuer: formNullable(item.issuer),
      issue_date: formNullable(item.issue_date),
      url: formNullable(normalizeProfileUrl(item.url)),
    })),
    projects: values.projects.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      name: item.name.trim(),
      description: formNullable(item.description),
      start_date: formNullable(item.start_date),
      end_date: formNullable(item.end_date),
      is_current: item.is_current,
      skills: item.skills.map((value) => value.trim()).filter(Boolean),
      url: formNullable(normalizeProfileUrl(item.url)),
    })),
  }
}

export const emptySkillForm = (): ProfileFormValues['skills'][number] => ({
  name: '',
  category: 'hard',
  level: '',
})

export const emptyExperienceForm = (): ProfileFormValues['experiences'][number] => ({
  job_title: '',
  company: '',
  location: '',
  employment_type: '',
  start_date: '',
  end_date: '',
  is_current: false,
  description: '',
  achievements: [],
  skills: [],
})

export const emptyEducationForm = (): ProfileFormValues['education'][number] => ({
  degree: '',
  level: '',
  field_of_study: '',
  institution: '',
  location: '',
  start_date: '',
  end_date: '',
  is_current: false,
  description: '',
})

export const emptyLanguageForm = (): ProfileFormValues['languages'][number] => ({
  name: '',
  code: '',
  level: '',
})

export const emptyCertificationForm = (): ProfileFormValues['certifications'][number] => ({
  name: '',
  issuer: '',
  issue_date: '',
  url: '',
})

export const emptyProjectForm = (): ProfileFormValues['projects'][number] => ({
  name: '',
  description: '',
  start_date: '',
  end_date: '',
  is_current: false,
  skills: [],
  url: '',
})
