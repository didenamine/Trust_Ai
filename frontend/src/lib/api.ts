import axios from 'axios'
import { getStoredToken } from './tokenStorage'

/**
 * Shared Axios instance for every call to the TrustAI API.
 * The base URL comes from VITE_API_URL (see .env.example).
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
})

// US01: attach the JWT (if any) to every outgoing request.
api.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
