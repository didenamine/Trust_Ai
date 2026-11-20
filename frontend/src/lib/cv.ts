import { isAxiosError } from 'axios'
import { api } from './api'

// Keep in sync with MAX_UPLOAD_SIZE_MB on the backend (the API stays the final check).
export const MAX_CV_SIZE_MB = 5
export const ACCEPTED_CV_EXTENSIONS = ['.pdf', '.docx']

export type CV = {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  uploaded_at: string
}

/** Returns an error message if the file can't be a valid CV, or null if it looks fine. */
export function validateCVFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ACCEPTED_CV_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return 'Format non accepté : seuls les fichiers PDF et DOCX sont acceptés.'
  }
  if (file.size === 0) {
    return 'Le fichier est vide.'
  }
  if (file.size > MAX_CV_SIZE_MB * 1024 * 1024) {
    return `Le fichier dépasse la taille maximale de ${MAX_CV_SIZE_MB} Mo.`
  }
  return null
}

/** The candidate's current CV, or null if they haven't imported one yet. */
export async function fetchCurrentCV(): Promise<CV | null> {
  try {
    const { data } = await api.get<CV>('/cv/me')
    return data
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}

export async function uploadCV(file: File): Promise<CV> {
  const formData = new FormData()
  formData.append('file', file)
  // The shared client defaults to JSON, and Axios would then convert the FormData to JSON.
  const { data } = await api.post<CV>('/cv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} Ko`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} Mo`
}

/** The API's error message (`detail`) if there is one, else a generic message. */
export function uploadErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return `${detail}.`
    }
  }
  return "L'import a échoué. Veuillez réessayer."
}
