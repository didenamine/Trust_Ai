import axios from 'axios'

/**
 * Shared Axios instance for every call to the TrustAI API.
 * The base URL comes from VITE_API_URL (see .env.example).
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
})

// US01 (Ikram): attach the JWT here once authentication is ready.
// api.interceptors.request.use((config) => { ... })
