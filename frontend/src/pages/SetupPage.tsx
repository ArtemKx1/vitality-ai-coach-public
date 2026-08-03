import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { apiFetch, useAuth } from "@/lib/auth"
import { SEO } from "@/components/SEO"

interface SetupStatus {
  setup_required: boolean
  locked: boolean
  llm_configured: boolean
  current_provider: string
  providers: string[]
}

interface ProviderDef {
  id: string
  name: string
  blurb: string
  badge?: string
  keyLabel?: string
  defaultModel: string
  needsModel: boolean
}

const PROVIDERS: ProviderDef[] = [
  { id: "groq", name: "Groq", blurb: "Very fast, generous free tier, no credit card needed.", badge: "Free tier", keyLabel: "API key", defaultModel: "llama-3.3-70b-versatile", needsModel: true },
  { id: "openrouter", name: "OpenRouter", blurb: "One key for hundreds of models, including free ones.", badge: "Free models", keyLabel: "API key", defaultModel: "", needsModel: false },
  { id: "openai", name: "OpenAI", blurb: "GPT-4o and other OpenAI models.", keyLabel: "API key", defaultModel: "gpt-4o", needsModel: true },
  { id: "mistral", name: "Mistral", blurb: "European cloud models, strong and affordable.", keyLabel: "API key", defaultModel: "mistral-small-latest", needsModel: true },
  { id: "google_ai", name: "Google AI", blurb: "Gemini models.", keyLabel: "API key", defaultModel: "gemini-2.0-flash", needsModel: true },
  { id: "openai_compatible", name: "Any OpenAI-compatible", blurb: "LM Studio, vLLM, Together, DeepSeek, Fireworks…", keyLabel: "API key (optional)", defaultModel: "", needsModel: true },
  { id: "ollama", name: "Ollama (local)", blurb: "100% private, runs on your own machine, free.", badge: "Offline", defaultModel: "gemma4:e4b", needsModel: true },
]

const MODEL_HINTS: Record<string, string> = {
  groq: "llama-3.3-70b-versatile",
  openrouter: "e.g. meta-llama/llama-3.3-70b-instruct:free",
  openai: "gpt-4o",
  mistral: "mistral-small-latest",
  google_ai: "gemini-2.0-flash",
  openai_compatible: "e.g. meta-llama/Llama-3.1-8B-Instruct",
  ollama: "gemma4:e4b",
}

export function SetupPage() {
  const navigate = useNavigate()
  const { user, register } = useAuth()

  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [step, setStep] = useState(1)

  // Step 1 — AI provider
  const [provider, setProvider] = useState("groq")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434")
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [setupError, setSetupError] = useState("")

  // Step 2 — account + Garmin
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [garminEmail, setGarminEmail] = useState("")
  const [garminPassword, setGarminPassword] = useState("")
  const [registering, setRegistering] = useState(false)
  const [registerError, setRegisterError] = useState("")

  const current = useMemo(() => PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0], [provider])

  useEffect(() => {
    if (user) {
      navigate("/app", { replace: true })
      return
    }
    apiFetch<SetupStatus>("/setup/status")
      .then((s) => {
        setStatus(s)
        if (PROVIDERS.some((p) => p.id === s.current_provider)) {
          setProvider(s.current_provider)
          setModel(MODEL_HINTS[s.current_provider] ?? "")
        }
      })
      .catch(() => setStatus(null))
  }, [user, navigate])

  if (status && !status.setup_required) {
    return (
      <div className="min-h-screen bg-paper-white flex items-center justify-center p-6">
        <SEO title="Setup" />
        <div className="w-full max-w-md text-center">
          <h1 className="font-inter text-2xl font-bold text-obsidian mb-3">Already configured</h1>
          <p className="font-inter text-sm text-charcoal mb-8">
            This instance already has an account. Settings are managed through environment variables now.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-obsidian text-paper-white font-inter text-sm font-semibold hover:opacity-80 transition-opacity"
          >
            Log in
          </Link>
        </div>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="min-h-screen bg-paper-white flex items-center justify-center p-6">
        <SEO title="Setup" />
        <p className="font-inter text-sm text-charcoal">Loading setup…</p>
      </div>
    )
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiFetch<{ ok: boolean; provider: string; response?: string }>("/setup/llm/test", {
        method: "POST",
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          model: current.needsModel ? model : undefined,
          base_url: provider === "openai_compatible" ? baseUrl : "",
          ollama_host: provider === "ollama" ? ollamaHost : "",
        }),
      })
      setTestResult({ ok: true, msg: res.response ? `Connected — model replied: “${res.response.trim()}”` : "Connected" })
    } catch (e) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : "Connection failed" })
    } finally {
      setTesting(false)
    }
  }

  async function handleSaveLLM() {
    setSaving(true)
    setSetupError("")
    try {
      await apiFetch<{ ok: boolean }>("/setup/llm", {
        method: "POST",
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          model: current.needsModel ? model : undefined,
          base_url: provider === "openai_compatible" ? baseUrl : "",
          ollama_host: provider === "ollama" ? ollamaHost : "",
        }),
      })
      setStep(2)
    } catch (e) {
      setSetupError(e instanceof Error ? e.message : "Could not save AI settings")
    } finally {
      setSaving(false)
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setRegistering(true)
    setRegisterError("")
    try {
      await register({
        email,
        password,
        full_name: fullName,
        garmin_email: garminEmail || undefined,
        garmin_password: garminPassword || undefined,
      })
      setStep(3)
    } catch (err) {
      setRegisterError(err instanceof Error ? err.message : "Registration failed")
    } finally {
      setRegistering(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper-white flex flex-col items-center px-6 py-10 lg:py-16">
      <SEO title="Setup" noindex />
      <Link to="/" className="flex items-center gap-2 mb-10">
        <div className="w-9 h-9 rounded-full bg-obsidian flex items-center justify-center">
          <span className="text-paper-white text-xs font-inter font-bold">V</span>
        </div>
        <span className="font-inter font-semibold text-sm text-obsidian">Vitality AI Coach</span>
      </Link>

      {/* Stepper */}
      <div className="flex items-center gap-2 mb-10">
        {["AI provider", "Your account", "Done"].map((label, i) => {
          const n = i + 1
          const active = step === n
          const done = step > n
          return (
            <div key={label} className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center font-inter text-xs font-bold transition-colors ${
                    done ? "bg-surgical-blue text-white" : active ? "bg-obsidian text-paper-white" : "bg-surface-container-low text-charcoal"
                  }`}
                >
                  {done ? "✓" : n}
                </div>
                <span className={`font-inter text-sm whitespace-nowrap ${active || done ? "text-obsidian" : "text-charcoal"}`}>{label}</span>
              </div>
              {n < 3 && <div className={`hidden sm:block w-10 h-px ${done ? "bg-surgical-blue" : "bg-outline-variant"}`} />}
            </div>
          )
        })}
      </div>

      <div className="w-full max-w-2xl">
        {step === 1 && (
          <div>
            <h1 className="font-inter text-2xl lg:text-3xl font-bold text-obsidian mb-2 text-center">Choose your AI provider</h1>
            <p className="font-inter text-sm text-charcoal mb-8 text-center">
              This powers all your coaching answers. Pick one — free tiers work fine.
            </p>

            <div className="grid sm:grid-cols-2 gap-3 mb-6">
              {PROVIDERS.map((p) => {
                const selected = provider === p.id
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setProvider(p.id)
                      setModel(MODEL_HINTS[p.id] ?? "")
                      setTestResult(null)
                    }}
                    className={`text-left p-4 rounded-xl border transition-all ${
                      selected
                        ? "border-surgical-blue bg-sky-tint/40 ring-1 ring-surgical-blue"
                        : "border-outline-variant/60 bg-surface-container-lowest hover:border-outline"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-inter text-sm font-semibold text-obsidian">{p.name}</span>
                      {p.badge && (
                        <span className="font-inter text-[11px] font-semibold text-surgical-blue bg-sky-tint/60 rounded-full px-2 py-0.5">{p.badge}</span>
                      )}
                    </div>
                    <p className="font-inter text-xs text-charcoal mt-1">{p.blurb}</p>
                  </button>
                )
              })}
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-5 space-y-4">
              {provider === "ollama" && (
                <div className="space-y-1.5">
                  <label className="block font-inter text-xs font-medium text-charcoal ml-1">Ollama host</label>
                  <input
                    type="text"
                    value={ollamaHost}
                    onChange={(e) => setOllamaHost(e.target.value)}
                    className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                  />
                  <p className="font-inter text-xs text-slate ml-1">
                    Make sure Ollama is running and the model is pulled. In Docker use <code className="font-mono">http://ollama:11434</code>.
                  </p>
                </div>
              )}
              {provider === "openai_compatible" && (
                <div className="space-y-1.5">
                  <label className="block font-inter text-xs font-medium text-charcoal ml-1">Base URL</label>
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="http://localhost:1234/v1"
                    className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                  />
                </div>
              )}
              {current.keyLabel && (
                <div className="space-y-1.5">
                  <label className="block font-inter text-xs font-medium text-charcoal ml-1">{current.keyLabel}</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={provider === "openai_compatible" ? "Optional for local endpoints" : "sk-…"}
                    autoComplete="off"
                    className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                  />
                </div>
              )}
              {current.needsModel && (
                <div className="space-y-1.5">
                  <label className="block font-inter text-xs font-medium text-charcoal ml-1">Model</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder={MODEL_HINTS[provider] ?? "model name"}
                    className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                  />
                </div>
              )}

              {testResult && (
                <div
                  className={`font-inter text-sm rounded-lg px-4 py-3 ${
                    testResult.ok ? "bg-sky-tint/50 text-obsidian" : "bg-error-container text-error"
                  }`}
                >
                  {testResult.msg}
                </div>
              )}
              {setupError && <div className="font-inter text-sm rounded-lg px-4 py-3 bg-error-container text-error">{setupError}</div>}

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={handleTest}
                  disabled={testing}
                  className="inline-flex items-center justify-center px-5 py-3 rounded-lg border border-outline-variant font-inter text-sm font-semibold text-obsidian hover:border-outline transition-colors disabled:opacity-50"
                >
                  {testing ? "Testing…" : "Test connection"}
                </button>
                <button
                  type="button"
                  onClick={handleSaveLLM}
                  disabled={saving}
                  className="flex-1 inline-flex items-center justify-center px-5 py-3 rounded-lg bg-obsidian text-paper-white font-inter text-sm font-semibold hover:opacity-80 transition-opacity disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Continue"}
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h1 className="font-inter text-2xl lg:text-3xl font-bold text-obsidian mb-2 text-center">Create your account</h1>
            <p className="font-inter text-sm text-charcoal mb-8 text-center">
              Your Garmin data stays on this server, encrypted. Optionally connect Garmin now.
            </p>
            <form onSubmit={handleRegister} className="bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-5 space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="su-name">Full name</label>
                  <input
                    id="su-name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="su-email">Email</label>
                  <input
                    id="su-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    autoComplete="email"
                    className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="su-password">Password</label>
                <input
                  id="su-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters, with a letter and a number"
                  autoComplete="new-password"
                  className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                />
              </div>

              <div className="border-t border-outline-variant/40 pt-4">
                <p className="font-inter text-xs font-medium text-charcoal mb-3">Connect your Garmin (recommended)</p>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="su-garmin-email">Garmin Connect email</label>
                    <input
                      id="su-garmin-email"
                      type="email"
                      value={garminEmail}
                      onChange={(e) => setGarminEmail(e.target.value)}
                      autoComplete="off"
                      className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="block font-inter text-xs font-medium text-charcoal ml-1" htmlFor="su-garmin-password">Garmin Connect password</label>
                    <input
                      id="su-garmin-password"
                      type="password"
                      value={garminPassword}
                      onChange={(e) => setGarminPassword(e.target.value)}
                      autoComplete="off"
                      className="w-full h-12 px-4 bg-paper-white border border-outline-variant/50 rounded-lg font-inter text-sm text-obsidian focus:border-surgical-blue focus:ring-1 focus:ring-surgical-blue outline-none transition-colors"
                    />
                  </div>
                </div>
                <p className="font-inter text-xs text-slate mt-2">
                  You can also connect it later from the Connect Garmin page.
                </p>
              </div>

              {registerError && <div className="font-inter text-sm rounded-lg px-4 py-3 bg-error-container text-error">{registerError}</div>}

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="inline-flex items-center justify-center px-5 py-3 rounded-lg border border-outline-variant font-inter text-sm font-semibold text-obsidian hover:border-outline transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={registering}
                  className="flex-1 inline-flex items-center justify-center px-5 py-3 rounded-lg bg-obsidian text-paper-white font-inter text-sm font-semibold hover:opacity-80 transition-opacity disabled:opacity-50"
                >
                  {registering ? "Creating account…" : "Create account & continue"}
                </button>
              </div>
            </form>
          </div>
        )}

        {step === 3 && (
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-sky-tint/60 flex items-center justify-center mx-auto mb-6">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2597d0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <h1 className="font-inter text-2xl lg:text-3xl font-bold text-obsidian mb-3">You're all set!</h1>
            <p className="font-inter text-sm text-charcoal mb-8 max-w-md mx-auto">
              Your coach is ready. Ask anything about your training, sleep, recovery or body battery — it answers using your real Garmin data.
            </p>
            <Link
              to="/app"
              className="inline-flex items-center justify-center px-8 py-3 rounded-lg bg-obsidian text-paper-white font-inter text-sm font-semibold hover:opacity-80 transition-opacity"
            >
              Start chatting →
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
