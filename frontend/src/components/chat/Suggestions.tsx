interface SuggestionsProps {
  userGarminConnected: boolean
  onSelect: (text: string) => void
  suggestions?: string[]
}

const staticSuggestionsGarmin = [
  "How was my last workout?",
  "What's my training load this week?",
  "Am I overtraining?",
  "How is my recovery?",
  "Summarize my last 7 days",
  "What workout should I do today?",
]

const staticSuggestionsNoGarmin = [
  "Create a weekly workout plan",
  "Tips for better sleep",
  "How to improve recovery?",
  "Best diet for endurance training",
  "How many rest days per week?",
  "What is HRV and why does it matter?",
]

export function Suggestions({ userGarminConnected, onSelect, suggestions }: SuggestionsProps) {
  const items = suggestions?.length
    ? suggestions
    : userGarminConnected
      ? staticSuggestionsGarmin
      : staticSuggestionsNoGarmin

  return (
    <div className="flex flex-wrap gap-2 max-w-3xl mx-auto max-h-20 md:max-h-none overflow-y-auto">
      {items.map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className="text-xs font-inter font-medium text-white bg-obsidian border border-obsidian rounded-full px-3.5 py-1.5 hover:bg-ink transition-colors cursor-pointer"
        >
          {s}
        </button>
      ))}
    </div>
  )
}
