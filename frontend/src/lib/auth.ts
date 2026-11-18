import { api } from './api'

export { clearStoredToken, getStoredToken, storeToken } from './tokenStorage'

export type User = {
  id: string
  email: string
  full_name: string | null
}

type Token = {
  access_token: string
  token_type: string
}

type PasswordResetRequestResult = {
  detail: string
  reset_token: string | null
}

export async function registerCandidate(input: {
  email: string
  password: string
  fullName?: string
}): Promise<User> {
  const { data } = await api.post<User>('/auth/register', {
    email: input.email,
    password: input.password,
    full_name: input.fullName || null,
  })
  return data
}

export async function login(input: { email: string; password: string }): Promise<string> {
  const { data } = await api.post<Token>('/auth/login', input)
  return data.access_token
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function requestPasswordReset(email: string): Promise<PasswordResetRequestResult> {
  const { data } = await api.post<PasswordResetRequestResult>('/auth/password-reset/request', {
    email,
  })
  return data
}

export async function confirmPasswordReset(input: {
  token: string
  newPassword: string
}): Promise<void> {
  await api.post('/auth/password-reset/confirm', {
    token: input.token,
    new_password: input.newPassword,
  })
}
