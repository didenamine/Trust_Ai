import { api } from './api'
import type { EducationLevel, SkillCategory } from './profile'

export type MatchingBand = 'excellent' | 'good' | 'moderate' | 'low'

export type DimensionScore = {
  weight: number
  points: number
  max_points: number
  ratio: number
}

export type SkillMatch = {
  name: string
  category: SkillCategory
  matched: boolean
}

export type ExperienceMatchDetail = {
  candidate_years: number
  required_years: number
  meets_requirement: boolean
}

export type EducationMatchDetail = {
  candidate_level: EducationLevel | null
  required_level: EducationLevel | null
  candidate_rank: number | null
  required_rank: number | null
  meets_requirement: boolean
}

export type MatchingDetails = {
  matched_skills: SkillMatch[]
  missing_skills: SkillMatch[]
  experience: ExperienceMatchDetail
  education: EducationMatchDetail
}

export type MatchingDimensionScores = {
  skills: DimensionScore
  experience: DimensionScore
  education: DimensionScore
}

export type MatchingResult = {
  total_score: number
  band: MatchingBand
  dimension_scores: MatchingDimensionScores
  details: MatchingDetails
  strengths: string[]
  improvements: string[]
}

export async function fetchMatching(offerId: string): Promise<MatchingResult> {
  const response = await api.get<MatchingResult>(`/matching/${offerId}`)
  return response.data
}
