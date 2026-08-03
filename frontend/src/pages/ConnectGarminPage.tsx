import { useEffect, useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { SEO } from "@/components/SEO"

function GlassPane({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`relative overflow-hidden shadow-[0_12px_40px_rgba(16,55,132,0.12),0_4px_16px_rgba(16,55,132,0.06)] ${className || ""}`} style={{ willChange: "transform" }}>
      <div className="absolute inset-0 z-0" style={{ backdropFilter: "blur(6px)", filter: "url(#glass-distortion)", isolation: "isolate" }} />
      <div className="absolute inset-0 z-[1]" style={{ background: "rgba(255, 255, 255, 0.3)" }} />
      <div className="absolute inset-0 z-[2]" style={{ boxShadow: "inset 0 1px 1px 0 rgba(255, 255, 255, 0.6), inset 0 -1px 1px 0 rgba(255, 255, 255, 0.2)" }} />
      <div className="relative z-[3] flex items-center w-full h-full">
        {children}
      </div>
    </div>
  )
}

const STATUS_PHRASES = [
  "Logging into Garmin Connect...",
  "Fetching your profile...",
  "Syncing your activities...",
  "Almost there...",
  "Just a moment...",
  "You're almost set up!",
]

function StatusRotator() {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((i) => (i + 1) % STATUS_PHRASES.length)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <span className="transition-opacity duration-300">
      {STATUS_PHRASES[index]}
    </span>
  )
}

export function ConnectGarminPage() {
  const { user, isLoading, connectGarmin } = useAuth()
  const navigate = useNavigate()
  const [garminEmail, setGarminEmail] = useState("")
  const [garminPassword, setGarminPassword] = useState("")
  const [agreed, setAgreed] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isLoading && !user) navigate("/login")
  }, [isLoading, user, navigate])

  if (!user) return null

  function validate() {
    if (!garminEmail) return "Please enter your Garmin email"
    if (!garminEmail.includes("@") || !garminEmail.includes(".")) return "Enter a valid email address"
    if (!garminPassword) return "Please enter your Garmin password"
    if (!agreed) return "You must agree to the Terms of Service and Privacy Policy"
    return ""
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    setError(validationError)
    if (validationError) return
    setLoading(true)
    try {
      await connectGarmin(garminEmail, garminPassword)
      navigate("/app")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect Garmin")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6"
      style={{ background: "linear-gradient(180deg, #779bc1 0%, #9abfda 58%, #cbdcec 100%)" }}
    >
      <SEO
        title="Connect Garmin"
        description="Connect your Garmin watch to Vitality AI Coach and start receiving personalized AI health and fitness insights."
        canonical="/connect-garmin"
        noindex
      />
      <svg className="absolute" style={{ width: 0, height: 0 }}>
        <defs>
          <filter id="glass-distortion" x="-10%" y="-10%" width="120%" height="120%" filterUnits="objectBoundingBox">
            <feTurbulence type="fractalNoise" baseFrequency="0.008" numOctaves="2" result="noise" />
            <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 6 -1.5" result="softNoise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      <GlassPane className="w-full max-w-sm rounded-[28px] p-10">
        <div className="flex flex-col w-full">
          <div className="flex items-center gap-2.5 mb-8">
            <div className="w-9 h-9 rounded-full bg-obsidian flex items-center justify-center">
              <span className="text-paper-white text-[11px] font-inter font-bold">V</span>
            </div>
            <span className="font-inter font-semibold text-sm tracking-[-0.01em] text-obsidian">Vitality AI Coach</span>
          </div>

          <h1 className="font-inter font-bold text-[26px] leading-[1.2] tracking-[-0.03em] text-obsidian mb-1.5">
            Connect your Garmin
          </h1>
          <p className="font-inter text-[15px] font-normal leading-relaxed text-charcoal/90 mb-9">
            Link your Garmin Connect account.<br />Credentials are encrypted end-to-end.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="block font-inter text-xs font-semibold text-obsidian ml-1" htmlFor="garminEmail">Garmin email</label>
              <input
                id="garminEmail"
                type="email"
                value={garminEmail}
                onChange={(e) => setGarminEmail(e.target.value)}
                placeholder="garmin@example.com"
                autoComplete="email"
                className="w-full h-13 px-[18px] bg-white/65 border border-white/50 rounded-2xl font-inter text-sm text-obsidian placeholder:text-charcoal/45 focus:border-white/90 focus:bg-white/80 focus:ring-0 outline-none transition-all"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block font-inter text-xs font-semibold text-obsidian ml-1" htmlFor="garminPassword">Garmin password</label>
              <input
                id="garminPassword"
                type="password"
                value={garminPassword}
                onChange={(e) => setGarminPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="password"
                className="w-full h-13 px-[18px] bg-white/65 border border-white/50 rounded-2xl font-inter text-sm text-obsidian placeholder:text-charcoal/45 focus:border-white/90 focus:bg-white/80 focus:ring-0 outline-none transition-all"
              />
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-charcoal/30 bg-white/60 text-obsidian focus:ring-obsidian focus:ring-offset-0 cursor-pointer"
              />
              <span className="font-inter text-xs leading-relaxed text-charcoal/80">
                I agree to the{" "}
                <Link to="/terms" className="text-obsidian font-medium underline underline-offset-2 hover:no-underline">Terms of Service</Link>
                {" "}and{" "}
                <Link to="/privacy" className="text-obsidian font-medium underline underline-offset-2 hover:no-underline">Privacy Policy</Link>
              </span>
            </label>

            {error && <p className="text-sm font-inter text-error font-medium">{error}</p>}

            {loading ? (
              <div className="mt-1 p-6 rounded-[20px] bg-white/75 border border-white/60 space-y-5">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-obsidian/5 flex items-center justify-center">
                      <div className="w-5 h-5 border-2 border-obsidian/30 border-t-obsidian rounded-full animate-spin" />
                    </div>
                    <div>
                      <p className="font-inter text-sm font-medium text-obsidian">Connecting to Garmin</p>
                      <p className="font-inter text-xs text-charcoal/80"><StatusRotator /></p>
                    </div>
                  </div>

                  <div className="w-full h-1.5 bg-obsidian/5 rounded-full overflow-hidden">
                    <div className="h-full bg-obsidian rounded-full animate-progress" />
                  </div>

                  <p className="font-inter text-[11px] text-charcoal/60 text-center">
                    This usually takes 30–60 seconds
                  </p>
                </div>
              </div>
            ) : (
              <button
                type="submit"
                disabled={!agreed}
                className="w-full bg-obsidian text-paper-white font-inter text-sm font-semibold h-13 rounded-full hover:opacity-90 active:scale-[0.98] transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed mt-1"
              >
                Connect Garmin
              </button>
            )}
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => navigate("/app")}
              className="font-inter text-[13px] font-medium text-charcoal/60 hover:text-charcoal transition-colors"
            >
              Skip for now
            </button>
          </div>
        </div>
      </GlassPane>
    </div>
  )
}
