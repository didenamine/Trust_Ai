import { isAxiosError } from 'axios'
import { api } from './api'
import type { SkillCategory } from './profile'

/**
 * US33: missing skills (US12) aggregated across every offer the candidate has
 * already analysed (US09), ranked by how often each one comes up missing.
 */

export type PrioritizedSkill = {
  name: string
  category: SkillCategory
  missing_in_offers: number
}

export type SkillGapResult = {
  skills: PrioritizedSkill[]
  offers_considered: number
}

/** Null means the candidate has no profile yet (US06/US07), not an empty result. */
export async function fetchSkillGaps(): Promise<SkillGapResult | null> {
  try {
    const { data } = await api.get<SkillGapResult>('/matching/skill-gaps')
    return data
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}
