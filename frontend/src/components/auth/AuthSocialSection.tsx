import { useEffect, useState } from "react"
import { supabase, supabaseConfigured } from "@/lib/supabase"

const VITE_BASE = import.meta.env.VITE_BASE || "/"
const AUTH_CALLBACK = `${window.location.origin}${VITE_BASE}/auth/callback`

const RATE_LIMIT_MESSAGES = ["email rate limit exceeded", "rate_limit", "too many requests", "captcha"]

function friendlyMagicError(raw: string): string {
  const lower = raw.toLowerCase()
  if (RATE_LIMIT_MESSAGES.some((m) => lower.includes(m))) {
    return "Too many requests from this IP. Try again in a few minutes."
  }
  return raw
}

interface AuthSocialSectionProps {
  footerText: string
}

export function AuthSocialSection({ footerText }: AuthSocialSectionProps) {
  const [showMagicInput, setShowMagicInput] = useState(false)
  const [magicEmail, setMagicEmail] = useState("")
  const [magicLinkSent, setMagicLinkSent] = useState(false)
  const [magicError, setMagicError] = useState("")
  const [magicCooldown, setMagicCooldown] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (magicCooldown <= 0) return
    const id = setInterval(() => setMagicCooldown((c) => c - 1), 1000)
    return () => clearInterval(id)
  }, [magicCooldown])

  const handleGoogleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: AUTH_CALLBACK },
    })
  }

  const handleMagicLink = async () => {
    setLoading(true)
    setMagicError("")
    const { error: err } = await supabase.auth.signInWithOtp({
      email: magicEmail,
      options: { emailRedirectTo: AUTH_CALLBACK },
    })
    setLoading(false)
    if (err) {
      const msg = friendlyMagicError(err.message)
      setMagicError(msg)
      if (msg !== err.message) {
        setMagicCooldown(60)
      }
    } else {
      setMagicLinkSent(true)
    }
  }

  return (
    <>
      <div className="flex items-center gap-4 my-6">
        <div className="flex-1 h-px bg-outline-variant/40" />
        <span className="text-xs font-inter text-slate uppercase tracking-wider">or</span>
        <div className="flex-1 h-px bg-outline-variant/40" />
      </div>
      {!supabaseConfigured ? (
        <p className="text-center font-inter text-xs text-slate">
          Social login is not configured on this instance.
        </p>
      ) : (
        <>
          {magicLinkSent ? (
        <div className="text-center py-6">
          <div className="w-12 h-12 rounded-full bg-obsidian/5 flex items-center justify-center mx-auto mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-obsidian">
              <path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </div>
          <p className="text-sm font-inter font-medium text-obsidian mb-1">Check your email</p>
          <p className="text-xs font-inter text-charcoal leading-relaxed">
            We sent a magic link to <span className="font-medium text-obsidian">{magicEmail}</span>.<br />
            Click it to sign in.
          </p>
          <button
            onClick={() => { setMagicLinkSent(false); setShowMagicInput(false); setMagicEmail("") }}
            className="mt-4 text-xs font-inter text-charcoal hover:text-obsidian underline underline-offset-2"
          >
            Use a different email
          </button>
        </div>
      ) : (
        <>
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 h-14 rounded-full border border-outline-variant/40 bg-paper-white font-inter text-sm font-medium text-obsidian hover:bg-surface-container-low active:scale-[0.98] transition-all duration-200"
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
          {showMagicInput ? (
            <div className="mt-3">
              <div className="flex items-center gap-2 h-14">
                <input
                  type="email"
                  value={magicEmail}
                  onChange={(e) => { setMagicEmail(e.target.value); setMagicError("") }}
                  placeholder="Enter your email"
                  autoFocus
                  className="flex-1 h-full px-4 bg-surface border border-outline-variant/50 rounded-xl font-inter text-sm text-obsidian placeholder:text-slate focus:border-obsidian focus:ring-1 focus:ring-obsidian outline-none transition-colors"
                  onKeyDown={(e) => { if (e.key === "Enter" && magicEmail.includes("@") && magicCooldown === 0) handleMagicLink() }}
                />
                <button
                  type="button"
                  onClick={handleMagicLink}
                  disabled={loading || !magicEmail.includes("@") || magicCooldown > 0}
                  className="h-full px-5 rounded-xl font-inter text-sm font-semibold text-paper-white disabled:opacity-40 transition-opacity shrink-0"
                  style={{ background: "linear-gradient(180deg, #779bc1 0%, #9abfda 58%, #cbdcec 100%)" }}
                >
                  {loading ? "..." : magicCooldown > 0 ? `${magicCooldown}s` : "Send"}
                </button>
              </div>
              {magicError && <p className="mt-2 text-xs font-inter text-error text-center">{magicError}</p>}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowMagicInput(true)}
              className="mt-3 w-full flex items-center justify-center gap-3 h-14 rounded-full font-inter text-sm font-semibold text-paper-white active:scale-[0.98] transition-all duration-200"
              style={{ background: "linear-gradient(180deg, #779bc1 0%, #9abfda 58%, #cbdcec 100%)" }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" />
              </svg>
              Send magic link
            </button>
          )}
        </>
        )}
      </>)}
      <p className="mt-6 text-center font-inter text-xs text-slate max-w-xs mx-auto leading-relaxed">
        {footerText}
      </p>
    </>
  )
}
