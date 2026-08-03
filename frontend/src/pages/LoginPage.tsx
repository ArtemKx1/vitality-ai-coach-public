import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { apiFetch, useAuth } from "@/lib/auth"
import { AuthLayout } from "@/components/auth/AuthLayout"

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  function validate() {
    if (!email) return "Please enter your email"
    if (!email.includes("@") || !email.includes(".")) return "Enter a valid email address"
    if (!password) return "Please enter your password"
    if (password.length < 8) return "Password must be at least 8 characters"
    return ""
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    setError(validationError)
    if (validationError) return
    setLoading(true)
    try {
      const user = await login(email, password)
      navigate(user.garmin_connected ? "/app" : "/connect-garmin")
    } catch {
      setError("Invalid email or password")
    } finally {
      setLoading(false)
    }
  }

  const [searchParams] = useSearchParams()

  useEffect(() => {
    const err = searchParams.get("error")
    if (err) setError(err)
    // Fresh instance without any account → force the setup wizard instead.
    apiFetch<{ setup_required: boolean }>("/setup/status").then((s) => {
      if (s.setup_required) navigate("/setup", { replace: true })
    })
  }, [searchParams, navigate])

  return (
    <AuthLayout
      title="Log In"
      description="Log in to your Vitality AI Coach account. Access your personalized AI health and fitness insights powered by your Garmin data."
      canonical="/login"
      activeTab="login"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="email">Email Address</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
            autoComplete="email"
            className="w-full h-14 px-4 bg-surface-container-lowest border border-outline-variant/50 rounded-xl font-inter text-base text-obsidian placeholder:text-slate focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
          />
        </div>
        <div className="space-y-1.5">
          <div className="flex justify-between items-center ml-1 pr-1">
            <label className="block font-inter text-xs font-medium text-charcoal" htmlFor="password">Password</label>
            <a href="#" className="font-inter text-xs text-surgical-blue hover:underline">Forgot password?</a>
          </div>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            className="w-full h-14 px-4 bg-surface-container-lowest border border-outline-variant/50 rounded-xl font-inter text-base text-obsidian placeholder:text-slate focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
          />
        </div>
        {error && <p className="text-sm font-inter text-error">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-obsidian text-paper-white font-inter text-base font-semibold h-14 rounded-full shadow-[0_4px_24px_rgba(16,55,132,0.03),0_1px_3px_rgba(16,55,132,0.02)] hover:opacity-90 active:scale-[0.98] transition-all duration-200 disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </AuthLayout>
  )
}
