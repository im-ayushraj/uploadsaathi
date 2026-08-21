import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { configureAuthHandlers } from '../../lib/api'
import {
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  signup as signupRequest,
  tokenStore,
  type LoginInput,
  type SignupInput,
  type User,
} from '../../lib/auth'

type AuthState = {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (input: LoginInput) => Promise<void>
  signup: (input: SignupInput) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => tokenStore.get())
  const [isLoading, setIsLoading] = useState<boolean>(() => Boolean(tokenStore.get()))

  const clearSession = useCallback(() => {
    tokenStore.clear()
    setToken(null)
    setUser(null)
  }, [])

  // Register handlers before any request goes out.
  useMemo(
    () => configureAuthHandlers({ getToken: () => tokenStore.get(), onUnauthorized: clearSession }),
    [clearSession],
  )

  // A token in localStorage is only a claim; confirm it with the backend.
  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    fetchMe()
      .then((me) => !cancelled && setUser(me))
      .catch(() => !cancelled && clearSession())
      .finally(() => !cancelled && setIsLoading(false))
    return () => {
      cancelled = true
    }
  }, [token, clearSession])

  const value = useMemo<AuthState>(
    () => ({
      user,
      isLoading,
      isAuthenticated: Boolean(user),
      login: async (input) => {
        const res = await loginRequest(input)
        tokenStore.set(res.access_token)
        setToken(res.access_token)
        setUser(res.user)
      },
      signup: async (input) => {
        const res = await signupRequest(input)
        tokenStore.set(res.access_token)
        setToken(res.access_token)
        setUser(res.user)
      },
      logout: async () => {
        await logoutRequest().catch(() => {})
        clearSession()
      },
    }),
    [user, isLoading, clearSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
