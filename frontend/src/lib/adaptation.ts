import axios from 'axios'
import { api } from './api'
import type { ContentLanguage } from './profile'

/**
 * US14 - the candidate's CV adapted to one offer.
 * Keep in sync with `backend/app/schemas/cv_adaptation.py`.
 */
export type AdaptedExperience = {
  /** Id of the matching experience in the candidate's profile. */
  experience_id: string
  description: string | null
  achievements: string[]
}

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

export type CVAdaptation = {
  id: string
  offer_id: string
  matching_score: number
  /** Skills the offer asks for that the profile does not have: never added to the CV. */
  missing_skills: string[]
  adapted_cv: AdaptedCV
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
