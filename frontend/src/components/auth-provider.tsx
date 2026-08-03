import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"

import type { AuthContextType, User } from "@/lib/auth"
import { AuthContext, apiFetch, clearToken, storeToken } from "@/lib/auth"
import { supabase } from "@/lib/supabase"

const SB_INIT_TIMEOUT = 8000

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"))
  const [isLoading, setIsLoading] = useState(true)
  const doneRef = useRef(false)
  const justLoggedInRef = useRef(false)

  const socialLogin = useCallback(async (email: string, fullName: string, provider: string, accessToken?: string) => {
    const res = await apiFetch<{ access_token: string; user: User }>("/auth/social-login", {
      method: "POST",
      body: JSON.stringify({ email, full_name: fullName, provider, token: accessToken || "" }),
    })
    storeToken(res.access_token)
    setToken(res.access_token)
    setUser(res.user)
    setIsLoading(false)
    justLoggedInRef.current = true
    return res.user
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiFetch<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
    storeToken(res.access_token)
    setToken(res.access_token)
    setUser(res.user)
    justLoggedInRef.current = true
    return res.user
  }, [])

  const register = useCallback(
    async (data: {
      email: string
      password: string
      full_name: string
      garmin_email?: string
      garmin_password?: string
    }) => {
      const res = await apiFetch<{ access_token: string; user: User }>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      })
      storeToken(res.access_token)
      setToken(res.access_token)
      setUser(res.user)
      justLoggedInRef.current = true
      return res.user
    },
    [],
  )

  const exchangeSupabaseSession = useCallback(async (session: any, retries = 1) => {
    if (doneRef.current || localStorage.getItem("token")) return
    doneRef.current = true
    const email = session.user.email!
    const name = session.user.user_metadata?.full_name || session.user.user_metadata?.name || email.split("@")[0]
    const provider = session.user.app_metadata?.provider || "google"
    const accessToken = session.access_token
    try {
      const u = await socialLogin(email, name, provider, accessToken)
      navigate(u.garmin_connected ? "/app" : "/connect-garmin", { replace: true })
    } catch (err) {
      doneRef.current = false
      const isRateLimit = err instanceof Error && (err as any).status === 429
      if (retries > 0 && !isRateLimit) {
        await new Promise((r) => setTimeout(r, 1500))
        return exchangeSupabaseSession(session, retries - 1)
      }
      setIsLoading(false)
      const msg = err instanceof Error ? err.message : "Sign-in failed"
      navigate(`/login?error=${encodeURIComponent(msg)}`, { replace: true })
    }
  }, [socialLogin, navigate])

  // Exchanges a Supabase session for a custom app token.
  // Called either from onAuthStateChange (pkce callback) or from getSession() (existing session on cold start).
  // The guard inside exchangeSupabaseSession prevents double processing.
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user && !localStorage.getItem("token")) {
        exchangeSupabaseSession(session)
      }
    })

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user && !localStorage.getItem("token")) {
        return exchangeSupabaseSession(session)
      }
      // The URL has a code but Supabase didn't find a session yet (PKCE still in flight).
      // Don't set isLoading(false) — the onAuthStateChange handler will fire SIGNED_IN
      // when the code exchange completes.
      const hasCode = new URLSearchParams(window.location.search).get("code")
      if (hasCode) {
        return
      }
      setIsLoading(false)
    })

    const fallbackTimer = setTimeout(() => {
      if (!doneRef.current && !localStorage.getItem("token")) {
        setIsLoading(false)
      }
    }, SB_INIT_TIMEOUT)

    return () => {
      subscription.unsubscribe()
      clearTimeout(fallbackTimer)
    }
  }, [exchangeSupabaseSession])

  useEffect(() => {
    if (token) {
      if (justLoggedInRef.current) {
        justLoggedInRef.current = false
        console.log("[Garmin:Auth] Just logged in, skipping /auth/me")
        setIsLoading(false)
        return
      }
      console.log("[Garmin:Auth] Token changed, fetching /auth/me...")
      apiFetch<User>("/auth/me")
        .then((u) => {
          console.log("[Garmin:Auth] /auth/me OK:", u.email, "id:", u.id)
          setUser(u)
        })
        .catch((e) => {
          console.error("[Garmin:Auth] /auth/me failed:", e?.status, e?.message)
          clearToken()
          setToken(null)
          setUser(null)
        })
        .finally(() => setIsLoading(false))
    }
  }, [token])

  const logout = useCallback(async () => {
    await supabase.auth.signOut().catch(() => {})
    clearToken()
    setToken(null)
    setUser(null)
  }, [])

  const connectGarmin = useCallback(
    async (garmin_email: string, garmin_password: string) => {
      const res = await apiFetch<User>("/auth/connect-garmin", {
        method: "POST",
        body: JSON.stringify({ garmin_email, garmin_password }),
      })
      setUser(res)
      return res
    },
    [],
  )

  const updateUser = useCallback((u: User) => {
    setUser(u)
  }, [])

  const value: AuthContextType = useMemo(
    () => ({ user, token, isLoading, login, register, socialLogin, logout, connectGarmin, updateUser }),
    [user, token, isLoading, login, register, socialLogin, logout, connectGarmin, updateUser],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
