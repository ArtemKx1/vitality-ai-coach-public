import { type RefObject, useCallback, useRef, useState } from "react"

interface ChatInputProps {
  input: string
  onInputChange: (value: string) => void
  onSend: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
  streaming: boolean
  inputRef: RefObject<HTMLInputElement | null>
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const w = typeof window !== "undefined" ? (window as any) : null
const isSpeechSupported = !!(w?.SpeechRecognition ?? w?.webkitSpeechRecognition)

export function ChatInput({ input, onInputChange, onSend, onKeyDown, streaming, inputRef }: ChatInputProps) {
  const [isRecording, setIsRecording] = useState(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)
  const baseInputRef = useRef("")

  const getRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.abort() } catch {}
      recognitionRef.current = null
    }
    const RecognitionCtor = w?.SpeechRecognition ?? w?.webkitSpeechRecognition
    if (!RecognitionCtor) return null
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition: any = new RecognitionCtor()
    recognition.lang = navigator.language || "en-US"
    recognition.interimResults = false
    recognition.continuous = false
    recognition.maxAlternatives = 1
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const results = event.results
      const last = results[results.length - 1]
      if (!last.isFinal) return
      const transcript = last[0].transcript
      const base = baseInputRef.current
      onInputChange(base + (base ? " " : "") + transcript)
    }
    recognition.onend = () => setIsRecording(false)
    recognition.onerror = () => setIsRecording(false)
    recognitionRef.current = recognition
    return recognition
  }, [onInputChange])

  const toggleMic = () => {
    const recognition = getRecognition()
    if (!recognition) return
    if (isRecording) {
      recognition.stop()
      setIsRecording(false)
    } else {
      baseInputRef.current = input
      try { recognition.start() } catch { setIsRecording(false) }
    }
  }

  return (
    <div className="flex items-center gap-3 max-w-3xl mx-auto">
      <div className="flex-1 flex items-center gap-2 bg-surface rounded-full px-4 py-2 border border-outline-variant/30">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask your AI coach..."
          disabled={streaming}
          className="flex-1 bg-transparent text-sm font-inter text-obsidian placeholder:text-slate outline-none"
        />
        {isSpeechSupported && (
          <button
            onClick={toggleMic}
            disabled={streaming}
            title={isRecording ? "Stop recording" : "Voice input"}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors shrink-0 ${
              isRecording
                ? "text-error bg-error/10"
                : "text-slate hover:text-obsidian"
            }`}
          >
            {isRecording ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="6" y="6" width="12" height="12" rx="1" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="2" width="6" height="12" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <line x1="12" y1="19" x2="12" y2="22" />
                <line x1="8" y1="22" x2="16" y2="22" />
              </svg>
            )}
          </button>
        )}
        <button
          onClick={onSend}
          disabled={streaming || !input.trim()}
          className="w-8 h-8 rounded-full bg-obsidian flex items-center justify-center disabled:opacity-30 transition-opacity shrink-0"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M1 13L13 7L1 1V6L9.5 7L1 8V13Z" fill="white" />
          </svg>
        </button>
      </div>
    </div>
  )
}
