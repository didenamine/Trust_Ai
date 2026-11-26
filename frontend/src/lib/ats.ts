import { isAxiosError } from 'axios'
import { api } from './api'
import { apiErrorMessage } from './cv'

export const ATS_QUERY_KEY = ['ats', 'me'] as const

export type ATSStatus = 'ok' | 'warning' | 'missing' | 'na'
export type ATSSectionId =
  'contact' | 'summary' | 'experience' | 'education' | 'skills' | 'certifications' | 'languages'
export type ATSBand = 'low' | 'to_improve' | 'good' | 'excellent'

export type ATSCriterion = {
  key: string
  label_key: string
  weight: number
  points: number
  status: ATSStatus
  applicable: boolean
  reason_code: string | null
}

export type ATSScore = {
  total: number
  band: ATSBand
  scoring_version: number
  denominator: number
  dimensions: ATSCriterion[]
  criteria: ATSCriterion[]
  na_sections: ATSSectionId[]
}

export type ATSSectionFinding = {
  section: ATSSectionId
  status: ATSStatus
  present: boolean
  detection: string
  line: number | null
  order_index: number | null
  checks: Record<string, boolean>
  issues: string[]
}

export type ATSKeywordSummary = {
  specific_count: number
  action_verb_count: number
  generic_count: number
  verified_count: number
  repeated_count: number
  max_occurrences: number
  specificity_ratio: number
  terminology_issues: number
}

export type ATSKeywordFinding = {
  canonical: string
  kind: 'hard_skill' | 'tool' | 'method' | 'action_verb' | 'generic'
  verified: boolean
  line: number | null
  section: ATSSectionId | null
  occurrences: number
  alias_count: number
  in_skills_section: boolean
  in_context_section: boolean
}

export type ATSReadabilityFinding = {
  code: string
  severity: 'info' | 'warning' | 'error'
  location: string
  page: number | null
  line: number | null
  degraded_extraction: boolean
  deduction: number
}

export type ATSAnalysisResult = {
  language: 'fr' | 'en'
  sections: ATSSectionFinding[]
  keywords: ATSKeywordSummary
  keyword_findings: ATSKeywordFinding[]
  readability: ATSReadabilityFinding[]
  score: ATSScore
  limitations: string[]
}

export type ATSAnalysisResponse = {
  id: string
  cv_document_id: string
  cv_uploaded_at: string
  created_at: string
  updated_at: string
  scoring_version: number
  score: ATSScore
  result: ATSAnalysisResult
}

/** The ATS result attached to the current CV, or null if none was run for it. */
export async function fetchATSAnalysis(): Promise<ATSAnalysisResponse | null> {
  try {
    const { data } = await api.get<ATSAnalysisResponse>('/ats/me')
    return data
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/** US24: run the ATS analysis manually for the imported CV. */
export async function analyzeCVForATS(): Promise<ATSAnalysisResponse> {
  const { data } = await api.post<ATSAnalysisResponse>('/ats/me/analyze')
  return data
}

export function atsErrorMessage(error: unknown): string {
  return apiErrorMessage(error, "L'analyse ATS a échoué. Veuillez réessayer.")
}
