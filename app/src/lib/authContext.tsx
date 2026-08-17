import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { UserRole } from './types'
import { ApiError, moliyaApi } from './apiClient'

export interface Session {
  actorId: string
  displayName: string
  role: UserRole
}

interface AuthContextValue {
  session: Session | null
  loading: boolean
  login: (username: string, password: string) => Promise<{ ok: boolean; error?: string }>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function toSession(response: { display_name: string; actor_id: string; role: UserRole }): Session {
  return {
    actorId: response.actor_id,
    displayName: response.display_name,
    role: response.role,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    moliyaApi
      .currentSession()
      .then((response) => setSession(toSession(response)))
      .catch(() => setSession(null))
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      loading,
      login: async (username: string, password: string) => {
        try {
          const response = await moliyaApi.login(username.trim(), password)
          setSession(toSession(response))
          return { ok: true }
        } catch (error) {
          return {
            ok: false,
            error: error instanceof ApiError ? error.message : 'Backendga ulanib bo‘lmadi',
          }
        }
      },
      logout: async () => {
        try {
          await moliyaApi.logout()
        } finally {
          setSession(null)
        }
      },
    }),
    [loading, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
