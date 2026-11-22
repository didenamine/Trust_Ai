import axios from 'axios'
import { api } from './api'
import type { ContentLanguage } from './profile'

/**
 * US14 - the candidate's CV adapted to one offer.
 * Keep in sync with `backend/app/schemas/cv_adaptation.py` and `schemas/ats_cv.py`.
 */
export type AdaptedExperience = {
  /** Id of the matching experience in the candidate's profile. */
  experience_id: string
  description: string | null
  achievements: string[]
}

/** The texts the LLM adapted, with what changed and why. */
export type AdaptedCV = {
  schema_version: 1
  language: ContentLanguage
  headline: string | null
  summary: string | null
  /** Profile skills, from the most to the least relevant for the offer. */
  highlighted_skills: string[]
  experiences: AdaptedExperience[]
  /** What was changed and why, for the candidate to review. */
  changes: string[]
}

export type CVContact = {
  full_name: string | null
  headline: string | null
  email: string | null
  phone: string | null
  location: string | null
  links: string[]
}

export type CVSkillGroup = { label: string; skills: string[] }

export type CVExperienceEntry = {
  job_title: string
  company: string | null
  location: string | null
  period: string | null
  description: string | null
  bullets: string[]
  technologies: string[]
}

export type CVEducationEntry = {
  degree: string
  institution: string | null
  location: string | null
  period: string | null
  description: string | null
}

export type CVProjectEntry = {
  name: string
  period: string | null
  description: string | null
  technologies: string[]
  url: string | null
}

export type CVCertificationEntry = { name: string; issuer: string | null; date: string | null }

export type CVLanguageEntry = { name: string; level: string | null }

/** The complete CV: one column, standard section titles, newest entries first. */
export type ATSCVDocument = {
  language: ContentLanguage
  contact: CVContact
  summary: string | null
  skill_groups: CVSkillGroup[]
  experiences: CVExperienceEntry[]
  projects: CVProjectEntry[]
  education: CVEducationEntry[]
  certifications: CVCertificationEntry[]
  languages: CVLanguageEntry[]
  /** Standard section titles in the CV's language, keyed by section id. */
  section_titles: Record<string, string>
  /** Standard sections the profile has nothing for: to complete in the profile. */
  missing_sections: string[]
}

export type CVAdaptation = {
  id: string
  offer_id: string
  matching_score: number
  /** Skills the offer asks for that the profile does not have: never added to the CV. */
  missing_skills: string[]
  adapted_cv: AdaptedCV
  document: ATSCVDocument
  /** The same CV as plain text, to copy or download. */
  ats_text: string
  created_at: string
  updated_at: string
}

/** US14: adapt the candidate's CV to an analysed offer (replaces any previous result). */
export async function adaptCV(offerId: string): Promise<CVAdaptation> {
  const { data } = await api.post<CVAdaptation>(`/adaptations/${offerId}`)
  return data
}

/** A readable message for a failed "adapt my CV" request. */
export function getAdaptationErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (error.response?.status === 429) {
      return "Trop d'analyses en peu de temps, réessayez dans une minute."
    }
    if (error.response?.status === 503) {
      return "Le service d'analyse est momentanément indisponible, réessayez plus tard."
    }
    if (error.response?.status === 401) return 'Votre session a expiré. Reconnectez-vous.'
  }
  return 'Impossible de joindre le serveur. Réessayez dans un instant.'
}
