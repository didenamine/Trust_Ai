import axios from 'axios'
import { api } from './api'
import type { OfferAnalysis } from './offerAnalysis'

export type JobOffer = {
  id: string
  source_type: 'url' | 'text'
  source_url: string | null
  content: string
  created_at: string
}

export type CreateOfferResult = {
  offer: JobOffer
  /** True when the offer was already in the user's list (the API answers 200 instead of 201). */
  alreadyAdded: boolean
}

/** US08: add an offer from a URL (its content is fetched by the API) or from pasted text. */
export async function createOffer(
  input: { url: string } | { text: string },
): Promise<CreateOfferResult> {
  const { data, status } = await api.post<JobOffer>('/offers', input)
  return { offer: data, alreadyAdded: status === 200 }
}

/** A readable message for a failed "add an offer" request. */
export function getOfferErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (error.response?.status === 422) return 'Les informations envoyées sont invalides.'
    if (error.response?.status === 401) return 'Votre session a expiré. Reconnectez-vous.'
  }
  return 'Impossible de joindre le serveur. Réessayez dans un instant.'
}

export type JobOfferSummary = {
  id: string
  source_type: 'url' | 'text'
  source_url: string | null
  title: string
  description: string
  /** When the signed-in candidate added the offer. */
  created_at: string
}

/** US08: the offers of the signed-in candidate, newest first. */
export async function fetchMyOffers(): Promise<JobOfferSummary[]> {
  const { data } = await api.get<JobOfferSummary[]>('/offers')
  return data
}

/** US08: remove an offer from the signed-in candidate's list. */
export async function deleteOffer(id: string): Promise<void> {
  try {
    await api.delete(`/offers/${id}`)
  } catch (error) {
    // Already removed (for example from another tab): the goal is reached.
    if (axios.isAxiosError(error) && error.response?.status === 404) return
    throw error
  }
}

/** US09: analyse a saved offer. Cached unless `refresh` is true. */
export async function analyzeOffer(id: string, refresh = false): Promise<OfferAnalysis> {
  const { data } = await api.post<OfferAnalysis>(
    `/offers/${id}/analyze`,
    null,
    refresh ? { params: { refresh: true } } : undefined,
  )
  return data
}

/** US09: the stored analysis, if any. */
export async function fetchOfferAnalysis(id: string): Promise<OfferAnalysis> {
  const { data } = await api.get<OfferAnalysis>(`/offers/${id}/analysis`)
  return data
}

/** A readable message for a failed "analyse an offer" request. */
export function getOfferAnalysisErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (error.response?.status === 429) {
      return "Trop d'analyses en peu de temps, réessayez dans une minute."
    }
    if (error.response?.status === 503) {
      return "Le service d'analyse est momentanément indisponible, réessayez plus tard."
    }
    if (error.response?.status === 422) return "Langue de l'offre non prise en charge."
    if (error.response?.status === 401) return 'Votre session a expiré. Reconnectez-vous.'
  }
  return 'Impossible de joindre le serveur. Réessayez dans un instant.'
}
