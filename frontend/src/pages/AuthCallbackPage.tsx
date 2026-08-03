import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "@/lib/auth"

const CALLBACK_TIMEOUT = 30000

export function AuthCallbackPage() {
  const { user, isLoading } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [state, setState] = useState<"waiting" | "timed_out" | "error">("waiting")
  const [errorMsg, setErrorMsg] = useState("")
  const handledRef = useRef(false)

  useEffect(() => {
    if (handledRef.current) return

    const error = params.get("error")
    const errorDescription = params.get("error_description")
    if (error) {
      handledRef.current = true
      navigate(`/login?error=${encodeURIComponent(errorDescription || error)}`, { replace: true })
      return
    }

    // If auth already resolved, navigate
    if (user) {
      handledRef.current = true
      navigate(user.garmin_connected ? "/app" : "/connect-garmin", { replace: true })
      return
    }

    // Wait: AuthProvider is processing the session — do NOT navigate ourselves,
    // let AuthProvider handle it via exchangeSupabaseSession. Navigating here
    // without setting the app token causes an infinite redirect loop.
  }, [user, isLoading, navigate, params])

  useEffect(() => {
    const timer = setTimeout(() => {
      setState("timed_out")
    }, CALLBACK_TIMEOUT)
    return () => clearTimeout(timer)
  }, [])

  if (state === "timed_out") {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <p className="text-sm font-inter text-error">Sign-in timed out. Please try again or contact support.</p>
          {errorMsg && <p className="text-xs font-inter text-charcoal">{errorMsg}</p>}
          <button
            onClick={() => navigate("/login")}
            className="text-sm font-inter text-obsidian underline hover:no-underline"
          >
            Back to login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-obsidian/20 border-t-obsidian rounded-full animate-spin" />
        <p className="text-sm font-inter text-charcoal">Completing sign in...</p>
      </div>
    </div>
  )
}
