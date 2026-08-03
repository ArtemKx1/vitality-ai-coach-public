interface HealthRange {
  earliest_date: string | null
  latest_date: string | null
  total_days: number
  backfill: {
    in_progress: boolean
    completed: number
    total: number
    percent: number
  } | null
}

interface User {
  garmin_connected: boolean
  full_name?: string
  email?: string
}

interface LobbyProps {
  user: User
  healthRange: HealthRange | null
  onSendMessage: (text: string) => void
}

function formatDate(iso: string | null) {
  if (!iso) return ""
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function Lobby({ user, healthRange, onSendMessage }: LobbyProps) {
  const suggestions = user.garmin_connected
    ? ["How was my last workout?", "What's my training load?", "How is my recovery?", "Summarize my last 7 days"]
    : ["Create a workout plan", "Tips for better sleep", "How to improve recovery?", "What is HRV?"]

  return (
    <div className="flex items-center justify-center h-full overflow-y-auto">
      <div className="w-full max-w-sm text-center space-y-5">
        <div className="w-16 h-16 rounded-full bg-obsidian mx-auto flex items-center justify-center">
          <span className="text-white text-2xl font-inter font-bold">AI</span>
        </div>
        <h2 className="text-2xl font-inter font-bold text-obsidian leading-tight">
          Your AI Health &<br />Fitness Coach
        </h2>
        <p className="text-base font-inter text-charcoal leading-relaxed max-w-xs mx-auto">
          {user.garmin_connected
            ? "I analyze your Garmin data to give you personalized coaching on training, recovery, sleep, and more."
            : "I'm your personal AI coach. Connect your Garmin for data-driven insights, or ask me general fitness questions."}
        </p>
        {user.garmin_connected && (
          <div className="space-y-2 pt-1">
            {!healthRange && (
              <p className="text-xs font-inter text-charcoal/60">Syncing your Garmin data...</p>
            )}
            {healthRange && healthRange.earliest_date && (
              <p className="text-xs font-inter text-charcoal/70">
                Your data from {formatDate(healthRange.earliest_date)} to today ({healthRange.total_days} days)
              </p>
            )}
            {healthRange?.backfill?.in_progress && (
              <div className="space-y-1">
                <div className="h-1 bg-outline-variant/30 rounded-full overflow-hidden max-w-[240px] mx-auto">
                  <div className="h-full bg-surgical-blue rounded-full transition-all" style={{ width: `${healthRange.backfill.percent}%` }} />
                </div>
                <p className="text-[11px] font-inter text-surgical-blue">
                  Backfilling your history... {healthRange.backfill.percent}%
                </p>
              </div>
            )}
          </div>
        )}
        <div className="flex flex-col items-center gap-2.5 pt-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSendMessage(s)}
              className="w-full max-w-xs text-sm font-inter text-charcoal border border-outline-variant/30 rounded-full px-5 py-2.5 hover:bg-surface hover:text-obsidian hover:border-obsidian/30 transition-colors cursor-pointer"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
