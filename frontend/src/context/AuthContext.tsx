import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import {
  changeAccountPassword,
  clearStoredToken,
  deleteAccount as deleteAccountRequest,
  fetchCurrentUser,
  getStoredToken,
  login as loginRequest,
  registerCandidate,
  storeToken,
  updateAccount as updateAccountRequest,
  type User,
} from '../lib/auth'

type AuthContextValue = {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  /** US02: update personal info; only the fields passed in are changed. */
  updateAccount: (input: { email?: string; fullName?: string }) => Promise<void>
  changePassword: (input: { currentPassword: string; newPassword: string }) => Promise<void>
  deleteAccount: () => Promise<void>
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

  const updateAccount = useCallback(async (input: { email?: string; fullName?: string }) => {
    setUser(await updateAccountRequest(input))
  }, [])

  const changePassword = useCallback(
    async (input: { currentPassword: string; newPassword: string }) => {
      await changeAccountPassword(input)
    },
    [],
  )

  const deleteAccount = useCallback(async () => {
    await deleteAccountRequest()
    clearStoredToken()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        register,
        logout,
        updateAccount,
        changePassword,
        deleteAccount,
      }}
    >
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
