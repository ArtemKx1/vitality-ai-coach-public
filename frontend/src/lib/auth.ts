import { createContext, useContext } from "react"

import { supabase } from "@/lib/supabase"

export interface User {
  id: number
  email: string
  full_name: string
  garmin_connected: boolean
  language: string
  created_at: string
  last_sync: string | null
  goal: string | null
  activities: string | null
  fitness_level: string | null
  equipment: string | null
  onboarding_completed: boolean
}

export interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
}

export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<User>
  register: (data: {
    email: string
    password: string
    full_name: string
    garmin_email?: string
    garmin_password?: string
  }) => Promise<User>
  socialLogin: (email: string, fullName: string, provider: string, accessToken?: string) => Promise<User>
  logout: () => Promise<void>
  connectGarmin: (garmin_email: string, garmin_password: string) => Promise<User>
  updateUser: (user: User) => void
}

export const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1"

async function doFetch<T>(path: string, options: RequestInit, token: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.text()
    let msg = body || res.statusText
    try {
      const parsed = JSON.parse(body)
      if (typeof parsed?.detail === "string") msg = parsed.detail
    } catch {
      // body is not JSON — keep the raw text
    }
    const err = new Error(msg)
    ;(err as any).status = res.status
    throw err
  }
  return res.json()
}

let refreshPromise: Promise<string | null> | null = null

async function tryRefreshToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.user?.email) return null

      const accessToken = session.access_token
      const res = await fetch(`${API_BASE}/auth/social-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: session.user.email,
          full_name: session.user.user_metadata?.full_name || session.user.email,
          provider: session.user.app_metadata?.provider || "google",
          token: accessToken || "",
        }),
      })
      if (!res.ok) return null
      const data = await res.json()
      storeToken(data.access_token)
      return data.access_token
    } catch {
      return null
    }
  })()
  const result = await refreshPromise
  refreshPromise = null
  return result
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let token = getStoredToken()
  console.log(`[Garmin:apiFetch] ${options.method || "GET"} ${path} - token: ${token ? token.substring(0, 20) + "..." : "null"}`)

  try {
    const result = await doFetch<T>(path, options, token)
    console.log(`[Garmin:apiFetch] ${path} - OK`)
    return result
  } catch (e: any) {
    console.error(`[Garmin:apiFetch] ${path} - error:`, e?.status, e?.message)
    if (e?.status === 401) {
      console.log(`[Garmin:apiFetch] ${path} - got 401, attempting token refresh...`)
      const newToken = await tryRefreshToken()
      if (newToken && newToken !== token) {
        console.log(`[Garmin:apiFetch] ${path} - token refreshed, retrying...`)
        const retryOptions = { ...options }
        if (retryOptions.headers) {
          const h = { ...(retryOptions.headers as Record<string, string>) }
          delete h["Authorization"]
          retryOptions.headers = h
        }
        return doFetch<T>(path, retryOptions, newToken)
      }
      console.log(`[Garmin:apiFetch] ${path} - token refresh failed`)
    }
    throw e
  }
}

export function storeToken(token: string) {
  localStorage.setItem("token", token)
}

export function getStoredToken(): string | null {
  return localStorage.getItem("token")
}

export function clearToken() {
  localStorage.removeItem("token")
}
