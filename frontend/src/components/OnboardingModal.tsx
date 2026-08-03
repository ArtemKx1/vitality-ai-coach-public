import { useState } from "react"

interface OnboardingData {
  goal: string
  activities: string[]
  fitness_level: string
  equipment: string
}

interface Props {
  onComplete: (data: OnboardingData) => void
}

const steps = [
  {
    key: "goal" as const,
    multi: false,
    title: "What's your goal?",
    options: [
      { value: "improve_fitness", label: "Improve fitness", icon: "🏃" },
      { value: "lose_weight", label: "Lose weight", icon: "⚖️" },
      { value: "event_preparation", label: "Prepare for an event", icon: "🎯" },
      { value: "general_health", label: "General health", icon: "💪" },
    ],
  },
  {
    key: "activities" as const,
    multi: true,
    title: "What do you do?",
    subtitle: "Pick all that apply",
    options: [
      { value: "running", label: "Running", icon: "🏃" },
      { value: "cycling", label: "Cycling", icon: "🚴" },
      { value: "swimming", label: "Swimming", icon: "🏊" },
      { value: "strength", label: "Strength training", icon: "🏋️" },
      { value: "mixed", label: "Mixed cardio", icon: "🔀" },
      { value: "yoga", label: "Yoga", icon: "🧘" },
      { value: "walking", label: "Walking", icon: "🚶" },
      { value: "other", label: "Other", icon: "🎯" },
    ],
  },
  {
    key: "fitness_level" as const,
    multi: false,
    title: "Your fitness level",
    options: [
      { value: "beginner", label: "Beginner", icon: "🌱", desc: "New to regular training" },
      { value: "intermediate", label: "Intermediate", icon: "📈", desc: "Train consistently" },
      { value: "advanced", label: "Advanced", icon: "🏆", desc: "Experienced athlete" },
    ],
  },
  {
    key: "equipment" as const,
    multi: false,
    title: "Where you train",
    options: [
      { value: "gym", label: "Gym", icon: "🏋️" },
      { value: "outdoor", label: "Outdoor", icon: "🌳" },
      { value: "home", label: "Home", icon: "🏠" },
    ],
  },
]

export function OnboardingModal({ onComplete }: Props) {
  const [step, setStep] = useState(0)
  const [data, setData] = useState<Partial<OnboardingData>>({
    activities: [],
  })
  const [selectedMulti, setSelectedMulti] = useState<Set<string>>(new Set())

  const current = steps[step]

  const selectSingle = (value: string) => {
    const newData = { ...data, [current.key]: value }
    setData(newData)
    if (step < steps.length - 1) {
      setStep(step + 1)
    } else {
      onComplete(newData as OnboardingData)
    }
  }

  const toggleMulti = (value: string) => {
    const next = new Set(selectedMulti)
    if (next.has(value)) {
      next.delete(value)
    } else {
      next.add(value)
    }
    setSelectedMulti(next)
  }

  const confirmMulti = () => {
    const values = Array.from(selectedMulti)
    const newData = { ...data, [current.key]: values }
    setData(newData)
    if (step < steps.length - 1) {
      setSelectedMulti(new Set())
      setStep(step + 1)
    } else {
      onComplete(newData as OnboardingData)
    }
  }

  const canContinue = current.multi ? selectedMulti.size > 0 : true

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-obsidian/30 backdrop-blur-sm">
      <div className="bg-paper-white rounded-[20px] shadow-xl p-6 w-[28rem] max-w-[94vw]">
        {/* Stepper */}
        <div className="relative mb-6">
          <div className="absolute top-4 left-0 right-0 h-px bg-outline-variant/50" />
          {step > 0 && (
            <div
              className="absolute top-4 left-0 h-px bg-obsidian transition-all duration-300"
              style={{ width: `${(step / (steps.length - 1)) * 100}%` }}
            />
          )}
          <div className="relative flex justify-between">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-inter font-semibold z-10 transition-colors ${
                  i <= step
                    ? "bg-obsidian text-paper-white"
                    : "bg-cloud-gray text-charcoal"
                } ${i === step ? "ring-2 ring-offset-2 ring-obsidian/20" : ""}`}
              >
                {i < step ? (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2 7.5L5.5 11L12 3" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs font-inter text-charcoal mb-1 text-center">
          Step {step + 1} of {steps.length}
        </p>

        <h2 className="text-lg font-inter font-semibold text-obsidian text-center mb-1">
          {current.title}
        </h2>
        {"subtitle" in current && current.subtitle && (
          <p className="text-xs font-inter text-charcoal text-center mb-5">{current.subtitle}</p>
        )}
        {!current.multi && (
          <p className="text-xs font-inter text-charcoal text-center mb-5">Choose one</p>
        )}

        <div className="space-y-2.5">
          {current.options.map((opt) => {
            const isSelected = current.multi ? selectedMulti.has(opt.value) : false
            return (
              <button
                key={opt.value}
                onClick={() => (current.multi ? toggleMulti(opt.value) : selectSingle(opt.value))}
                className={`w-full flex items-center gap-3 p-3.5 rounded-xl border transition-all text-left cursor-pointer group ${
                  isSelected
                    ? "border-obsidian bg-obsidian/5"
                    : "border-outline-variant/30 hover:border-obsidian/30 hover:bg-surface"
                }`}
              >
                <span className="text-xl shrink-0">{opt.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-inter font-medium text-obsidian">{opt.label}</p>
                  {"desc" in opt && opt.desc && (
                    <p className="text-xs font-inter text-charcoal mt-0.5">{opt.desc}</p>
                  )}
                </div>
                {current.multi && (
                  <div
                    className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${
                      isSelected ? "bg-obsidian border-obsidian" : "border-outline-variant"
                    }`}
                  >
                    {isSelected && (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M1.5 5.5L4 8L8.5 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {current.multi && (
          <div className="mt-5 flex justify-end">
            <button
              onClick={confirmMulti}
              disabled={!canContinue}
              className="bg-obsidian text-paper-white text-sm font-inter font-medium px-6 py-2.5 rounded-full disabled:opacity-30 disabled:cursor-not-allowed transition-opacity cursor-pointer"
            >
              {step < steps.length - 1 ? "Continue" : "Start coaching"}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
