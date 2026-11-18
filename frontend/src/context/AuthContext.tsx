import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import {
  clearStoredToken,
  fetchCurrentUser,
  getStoredToken,
  login as loginRequest,
  registerCandidate,
  storeToken,
  type User,
} from '../lib/auth'

type AuthContextValue = {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!getStoredToken()) {
      setIsLoading(false)
      return
    }
    fetchCurrentUser()
      .then(setUser)
      .catch(() => clearStoredToken())
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const token = await loginRequest({ email, password })
    storeToken(token)
    setUser(await fetchCurrentUser())
  }, [])

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await registerCandidate({ email, password, fullName })
      await login(email, password)
    },
    [login],
  )

  const logout = useCallback(() => {
    clearStoredToken()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
