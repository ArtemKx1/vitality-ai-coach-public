import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { apiFetch } from "@/lib/auth"
import { AuthLayout } from "@/components/auth/AuthLayout"

export function SignupPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  // On a fresh instance (no accounts yet), send users through the setup wizard
  // which configures the AI provider first.
  useEffect(() => {
    apiFetch<{ setup_required: boolean }>("/setup/status")
      .then((s) => {
        if (s.setup_required) navigate("/setup", { replace: true })
      })
      .catch(() => {})
  }, [navigate])

  function validate() {
    if (!fullName || fullName.trim().length < 2) return "Full name must be at least 2 characters"
    if (!email) return "Please enter your email"
    if (!email.includes("@") || !email.includes(".")) return "Enter a valid email address"
    if (!password) return "Please enter a password"
    if (password.length < 8) return "Password must be at least 8 characters"
    if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) return "Password must contain at least one letter and one number"
    return ""
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    setError(validationError)
    if (validationError) return
    setLoading(true)
    try {
      await register({ email, password, full_name: fullName })
      navigate("/connect-garmin")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Sign Up"
      description="Create your free Vitality AI Coach account. Connect your Garmin watch and get personalized AI health and fitness coaching."
      canonical="/signup"
      activeTab="signup"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="fullName">Full Name</label>
          <input
            id="fullName"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g. Jane Doe"
            autoComplete="name"
            className="w-full h-14 px-4 bg-surface-container-lowest border border-outline-variant/50 rounded-xl font-inter text-base text-obsidian placeholder:text-slate focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
          />
        </div>
        <div className="space-y-1.5">
          <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="email">Email Address</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="hello@example.com"
            autoComplete="email"
            className="w-full h-14 px-4 bg-surface-container-lowest border border-outline-variant/50 rounded-xl font-inter text-base text-obsidian placeholder:text-slate focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
          />
        </div>
        <div className="space-y-1.5">
          <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="new-password"
            className="w-full h-14 px-4 bg-surface-container-lowest border border-outline-variant/50 rounded-xl font-inter text-base text-obsidian placeholder:text-slate focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
          />
        </div>
        {error && <p className="text-sm font-inter text-error">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-obsidian text-paper-white font-inter text-base font-semibold h-14 rounded-full shadow-[0_4px_24px_rgba(16,55,132,0.03),0_1px_3px_rgba(16,55,132,0.02)] hover:opacity-90 active:scale-[0.98] transition-all duration-200 disabled:opacity-50"
        >
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>
    </AuthLayout>
  )
}
